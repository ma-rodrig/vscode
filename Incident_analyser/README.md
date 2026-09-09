# Incident Analyser

Mini projeto Python que lê incidentes a partir de um ficheiro JSON e
classifica cada um por severidade (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`),
usando um classificador simples baseado em regras.

## Como funciona a classificação

Para cada incidente, aplicam-se três camadas de regras, por ordem:

1. **Palavras-chave** no título/descrição (ex.: "outage", "down" →
   `CRITICAL`; "degraded" → `HIGH`; "slow" → `MEDIUM`; "typo" → `LOW`).
2. **Fallback por impacto**: se nenhuma keyword corresponder, usa o número
   de `affected_users` (ex.: ≥10 000 → `CRITICAL`, ≥1 000 → `HIGH`, etc.).
3. **Escalonamento por serviço crítico**: incidentes em serviços como
   `payments`, `auth`, `checkout` ou `database` nunca ficam abaixo de
   `HIGH`, mesmo que as regras anteriores dessem uma severidade menor.

Cada incidente guarda também as `reasons` (razões) que levaram à
severidade final, para facilitar a auditoria da decisão.

## Estrutura do projeto

```
incident_analyser/
├── incident_analyser.py       # lógica principal + CLI
├── sample_incidents.json      # dados de exemplo
└── README.md
```

## Como usar

```bash
# Analisar e imprimir o resumo no terminal
python incident_analyser.py sample_incidents.json

# Analisar e gravar o relatório completo em JSON
python incident_analyser.py sample_incidents.json --output report.json
```

## Formato do JSON de entrada

```json
[
  {
    "id": "INC-001",
    "title": "Payments service outage",
    "description": "Checkout is completely down.",
    "service": "payments",
    "affected_users": 15000,
    "timestamp": "2026-09-08T10:15:00Z"
  }
]
```

Campos: `id`, `title`, `description`, `service`, `affected_users`
(número), `timestamp` (opcional, apenas informativo).

## Correr os testes

```bash
python -m unittest test_incident_analyser.py -v
```
