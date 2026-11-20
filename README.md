# SOS Driver — Automação de triagem de prestadores

Projeto acadêmico CitizenTech desenvolvido por:

- **Jessica Witzler Costacurta** — RM99068
- **Marcio Hitoshi Tahyra** — RM552511


## 1. Sobre o projeto

A SOS Driver busca conectar motoristas que precisam de assistência veicular a prestadores de serviços. Este módulo automatiza a triagem inicial dos cadastros de prestadores, reduzindo conferências repetitivas e padronizando a classificação dos registros.

A automação recebe um lote CSV, valida os campos e classifica cada cadastro como `aprovado`, `reprovado` ou `revisao_manual`. Somente os registros aprovados são enviados à API do MVP.

A classificação `revisao_manual` indica que há pendências no cadastro; o workflow não executa uma revisão humana.

## 2. Arquitetura

```text
Arquivo CSV
    |
    v
n8n (leitura e extração)
    |
    v
JavaScript (validações e classificação por cadastro)
    |
    +---- reprovado / revisão manual ----+
    |                                    |
    +---- aprovado --> HTTP POST         |
                         |               |
                         v               |
                  FastAPI / Pydantic     |
                         |               |
                         v               |
                      SQLite             |
                         |               |
                         +-------+-------+
                                 v
                       Consolidação e log TXT
```

- **CSV:** entrada em lote.
- **n8n:** orquestração das etapas, decisões, integração e geração do log.
- **JavaScript:** validação dos dados e classificação dos cadastros.
- **Python + FastAPI + Pydantic:** API do MVP que recebe os aprovados.
- **SQLite:** persistência dos prestadores.
- **Docker:** execução do n8n em contêiner.

## 3. Estrutura do repositório

```text
SOSDriver-n8n/   
├── backend/
│   ├── __pycache__
│   ├── main.py
│   ├── prestadores_api.py
│   └── sosdriver.db
├── logs/
│   └── log_triagem_20261119191732.txt
└── data/
│   └── cadastros_prestadores.csv
├── n8n/
    └── sosdriver_triagem_prestadores.json
```

## 4. Tecnologias utilizadas

| Tecnologia | Utilização |
|---|---|
| n8n | Orquestração do workflow |
| JavaScript | Regras de validação e classificação |
| Python | Implementação da API |
| FastAPI | Endpoints HTTP do MVP |
| SQLite | Persistência dos prestadores |
| Docker | Execução do n8n em contêiner |

## 5. Critérios de validação e decisões

O workflow verifica:

- Presença das colunas obrigatórias.
- Validade matemática de CPF/CNPJ.
- Duplicidade de documento dentro do lote.
- Validade da habilitação.
- Formato sintático do e-mail.
- Quantidade de dígitos do telefone.
- Tipo de serviço permitido: guincho, mecânico, socorrista ou chaveiro.
- Cidade dentro da cobertura configurada: São Paulo, Guarulhos, Osasco, Santo André, São Bernardo do Campo e São Caetano do Sul.

A prioridade de classificação é: havendo motivo de reprovação, o cadastro é reprovado; sem reprovação, mas com pendência, recebe `revisao_manual`; sem inconsistências, é aprovado.

## 6. Como executar

### 6.1 Backend

Pré-requisitos: Python 3.10 ou superior e dependências:

```bash
pip install fastapi uvicorn pydantic
```

Configure a variável de ambiente `SOSDRIVER_API_KEY` com uma chave definida para o ambiente. Opcionalmente, configure `SOSDRIVER_DB` para indicar o caminho do banco SQLite.

No Windows PowerShell:

```powershell
$env:SOSDRIVER_API_KEY="sua-chave-local"
$env:SOSDRIVER_DB="sosdriver.db"
uvicorn app:app --reload
```

O arquivo `src/prestadores_api.py` define um `APIRouter`. Ele deve ser incluído na aplicação FastAPI principal:

```python
from prestadores_api import router
app.include_router(router)
```

A documentação interativa da API fica disponível em `/docs`, conforme a configuração do servidor.

### 6.2 n8n

1. Inicie o contêiner n8n.
2. Importe `n8n/sosdriver_triagem_prestadores.json`.
3. Disponibilize o CSV no caminho configurado no nó **Ler lote de cadastros**: `/home/node/.n8n-files/cadastros_prestadores.csv`.
4. No nó **Enviar ao MVP**, configure a URL da API acessível a partir do contêiner. Em Docker Desktop, `host.docker.internal` pode ser necessário para acessar o host.
5. Configure o cabeçalho `x-api-key` usando uma credencial segura do n8n. O texto `CONFIGURAR_CREDENCIAL_NO_N8N` no JSON é apenas um marcador e não é uma chave válida.
6. Execute o workflow manualmente e confira a resposta da API e o arquivo de log.

O workflow usa gatilho manual. Portanto, uma pessoa precisa iniciar cada execução.

## 7. Integração com o MVP

- `POST /prestadores`: recebe os cadastros aprovados, autentica pelo cabeçalho `x-api-key` e realiza inserção/atualização no SQLite.
- `GET /prestadores`: lista prestadores ativos e permite filtros por cidade e tipo de serviço.

A integração foi exercitada no ambiente de desenvolvimento: três cadastros aprovados foram enviados e confirmados no SQLite. Consulte a documentação técnica e as evidências visuais em `docs/` e `assets/`.

## 8. Testes

O lote demonstrativo processado tinha oito registros: três aprovados e enviados, três reprovados e dois classificados como `revisao_manual`.

Os cenários efetivamente executados e os cenários ainda pendentes estão discriminados em [`tests/README.md`](tests/README.md). Não considere cenários marcados como pendentes como testes concluídos.

## 9. Logs e auditoria

O workflow gera log TXT com horário, contagens, identificador externo, documento mascarado, status e motivos. O ambiente utilizado gravava os arquivos dentro do contêiner n8n; como não havia volume Docker persistente, foi necessário copiar o log manualmente para a pasta local.

A pasta `logs/` contém somente um exemplo sanitizado, não um log bruto com dados pessoais.

## 10. Segurança e LGPD

- Use somente dados fictícios ou anonimizados no repositório público.
- Não publique arquivos `.env`, chaves, banco SQLite com dados pessoais, CSVs reais ou logs brutos.
- Configure a chave da API por variável de ambiente no backend e credencial no n8n.
- Restrinja o acesso ao CSV, API, banco e logs.
- Defina finalidade, base legal, retenção e controle de acesso conforme as diretrizes do projeto e a LGPD.

O protótipo não deve ser considerado pronto para produção sem as melhorias e testes pendentes descritos na documentação técnica.

## 11. Links da entrega

- **Vídeo demonstrativo:** https://youtu.be/8FvgLmfFE6k
