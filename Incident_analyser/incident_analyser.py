"""
Incident Analyser
==================

Mini projeto que lê incidentes a partir de um ficheiro JSON e classifica
cada um deles por severidade (CRITICAL, HIGH, MEDIUM, LOW), com base em:

- palavras-chave presentes no título/descrição
- número de utilizadores afetados
- se o serviço afetado está marcado como crítico para o negócio

Uso:
    python incident_analyser.py sample_incidents.json
    python incident_analyser.py sample_incidents.json --output relatorio.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuração da classificação
# ---------------------------------------------------------------------------

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# Palavras-chave associadas a cada nível de severidade.
# São procuradas (case-insensitive) no título + descrição do incidente.
KEYWORDS_BY_SEVERITY: dict[str, list[str]] = {
    "CRITICAL": ["outage", "down", "data loss", "breach", "unavailable", "crash"],
    "HIGH": ["degraded", "failure", "error rate", "timeout", "latency spike"],
    "MEDIUM": ["slow", "intermittent", "warning", "delay"],
    "LOW": ["cosmetic", "typo", "minor", "ui glitch"],
}

# Serviços considerados críticos para o negócio: sobem a severidade
# calculada em pelo menos um nível (nunca abaixo de HIGH).
CRITICAL_SERVICES = {"payments", "auth", "checkout", "database"}

# Thresholds de utilizadores afetados usados quando nenhuma keyword bate certo.
USER_IMPACT_THRESHOLDS = [
    (10_000, "CRITICAL"),
    (1_000, "HIGH"),
    (100, "MEDIUM"),
    (0, "LOW"),
]


@dataclass
class Incident:
    id: str
    title: str
    description: str
    service: str
    affected_users: int
    timestamp: str
    severity: str = field(default="", init=False)
    reasons: list[str] = field(default_factory=list, init=False)

    @property
    def text(self) -> str:
        return f"{self.title} {self.description}".lower()


# ---------------------------------------------------------------------------
# Lógica de classificação
# ---------------------------------------------------------------------------

def classify_by_keywords(incident: Incident) -> str | None:
    """Devolve a severidade se alguma keyword coincidir, senão None."""
    text = incident.text
    for severity in SEVERITY_ORDER:
        for keyword in KEYWORDS_BY_SEVERITY[severity]:
            if keyword in text:
                incident.reasons.append(f"keyword '{keyword}' -> {severity}")
                return severity
    return None


def classify_by_user_impact(incident: Incident) -> str:
    """Fallback: classifica pelo número de utilizadores afetados."""
    for threshold, severity in USER_IMPACT_THRESHOLDS:
        if incident.affected_users >= threshold:
            incident.reasons.append(
                f"{incident.affected_users} utilizadores afetados -> {severity}"
            )
            return severity
    return "LOW"


def escalate_if_critical_service(incident: Incident, severity: str) -> str:
    """Garante que incidentes em serviços críticos nunca ficam abaixo de HIGH."""
    if incident.service.lower() in CRITICAL_SERVICES:
        current_rank = SEVERITY_ORDER.index(severity)
        high_rank = SEVERITY_ORDER.index("HIGH")
        if current_rank > high_rank:
            incident.reasons.append(
                f"serviço crítico '{incident.service}' -> escalado para HIGH"
            )
            return "HIGH"
    return severity


def classify_incident(incident: Incident) -> str:
    """Aplica as regras, por ordem de prioridade, e devolve a severidade final."""
    severity = classify_by_keywords(incident)
    if severity is None:
        severity = classify_by_user_impact(incident)

    severity = escalate_if_critical_service(incident, severity)
    incident.severity = severity
    return severity


# ---------------------------------------------------------------------------
# Carregamento / relatório
# ---------------------------------------------------------------------------

def load_incidents(path: Path) -> list[Incident]:
    with path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)

    incidents = []
    for item in data:
        incidents.append(
            Incident(
                id=str(item.get("id", "unknown")),
                title=item.get("title", ""),
                description=item.get("description", ""),
                service=item.get("service", ""),
                affected_users=int(item.get("affected_users", 0)),
                timestamp=item.get("timestamp", ""),
            )
        )
    return incidents


def build_report(incidents: list[Incident]) -> dict[str, Any]:
    counts = Counter(inc.severity for inc in incidents)
    ordered = sorted(
        incidents, key=lambda inc: SEVERITY_ORDER.index(inc.severity)
    )

    return {
        "total_incidents": len(incidents),
        "counts_by_severity": {s: counts.get(s, 0) for s in SEVERITY_ORDER},
        "incidents": [
            {
                "id": inc.id,
                "title": inc.title,
                "service": inc.service,
                "affected_users": inc.affected_users,
                "severity": inc.severity,
                "reasons": inc.reasons,
            }
            for inc in ordered
        ],
    }


def print_summary(report: dict[str, Any]) -> None:
    print(f"\nTotal de incidentes analisados: {report['total_incidents']}\n")
    print("Contagem por severidade:")
    for severity in SEVERITY_ORDER:
        print(f"  {severity:<8} {report['counts_by_severity'][severity]}")

    print("\nDetalhe (ordenado por severidade):")
    for inc in report["incidents"]:
        print(f"  [{inc['severity']:<8}] {inc['id']} - {inc['title']} "
              f"(serviço: {inc['service']}, utilizadores: {inc['affected_users']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Incident Analyser")
    parser.add_argument("input", type=Path, help="Ficheiro JSON com incidentes")
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Ficheiro JSON onde gravar o relatório (opcional)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Erro: ficheiro '{args.input}' não encontrado.", file=sys.stderr)
        return 1

    incidents = load_incidents(args.input)
    for incident in incidents:
        classify_incident(incident)

    report = build_report(incidents)
    print_summary(report)

    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nRelatório gravado em: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
