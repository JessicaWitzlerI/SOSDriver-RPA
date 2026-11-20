# SOS Driver — Automação de triagem de prestadores

Projeto acadêmico CitizenTech (Global Solution 2026.2, FIAP) desenvolvido por:

- Jessica Witzler Costacurta — RM99068
- Marcio Hitoshi Tahyra — RM552511

## 1. Sobre o projeto

A SOS Driver busca conectar motoristas que precisam de assistência veicular a prestadores de serviços. Este módulo automatiza a triagem inicial dos cadastros de prestadores, reduzindo conferências repetitivas e padronizando a classificação dos registros.

A automação recebe um lote CSV, valida os campos e classifica cada cadastro como `aprovado`, `reprovado` ou `revisao_manual`. Somente os registros aprovados são enviados à API do MVP.

A classificação `revisao_manual` indica que há pendências no cadastro; o workflow não executa uma revisão humana.

## 2. Arquitetura

```
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

O fluxograma do processo em BPMN está em `docs/sosdriver_triagem.bpmn` (imagem em `docs/sosdriver_triagem.png`).

## 3. Estrutura do repositório

```
SOSDriver-n8n/
├── backend/
│   ├── main.py
│   ├── prestadores_api.py
│   └── requirements.txt
├── data/
│   └── cadastros_prestadores.csv           
├── logs/
│   └── log_triagem_20261119191732.txt
├── n8n/
│   └── sosdriver_triagem_prestadores.json
├── .gitignore
└── README.md
```

O banco `sosdriver.db` e a pasta `__pycache__/` são gerados na execução e ficam fora do repositório (`.gitignore`).

## 4. Tecnologias utilizadas

| Tecnologia | Utilização |
|---|---|
| n8n | Orquestração do workflow |
| JavaScript | Regras de validação e classificação |
| Python | Implementação da API |
| FastAPI / Pydantic | Endpoints HTTP e validação do payload do MVP |
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
- Tipo de serviço permitido: `guincho`, `mecanico`, `socorrista` ou `chaveiro`.
- Cidade dentro da cobertura configurada: São Paulo, Guarulhos, Osasco, Santo André, São Bernardo do Campo e São Caetano do Sul.

| Situação encontrada | Classificação |
|---|---|
| CPF/CNPJ inválido | `reprovado` |
| Documento duplicado no lote | `reprovado` |
| Habilitação/licença vencida | `reprovado` |
| Data de validade ausente ou ilegível | `revisao_manual` |
| E-mail ou telefone inválido | `revisao_manual` |
| Tipo de serviço desconhecido | `revisao_manual` |
| Cidade fora da cobertura | `revisao_manual` |
| Nenhuma inconsistência | `aprovado` |

A prioridade de classificação é: havendo motivo de reprovação, o cadastro é reprovado; sem reprovação, mas com pendência, recebe `revisao_manual`; sem inconsistências, é aprovado.

## 6. Lógica de negócio e processamento em lote

- **Estrutura de repetição:** o nó de código "Validar cadastros" percorre, com um laço `for`, todos os cadastros do lote e aplica as regras a cada um.
- **Estruturas de decisão:** a classificação em três status (condicionais no mesmo nó) e o nó "Aprovado?", que desvia apenas os aprovados para o envio ao MVP.
- Os resultados de todos os caminhos são reunidos no nó "Juntar resultados" e consolidados em um único log.

## 7. Exceções e resiliência

| Falha prevista | Tratamento |
|---|---|
| Arquivo CSV ausente | O nó de leitura sempre emite um item; o nó "Arquivo encontrado?" desvia o fluxo para o registro "LOTE NAO PROCESSADO" no log. |
| Arquivo vazio ou sem colunas obrigatórias | O lote recebe o status `lote_invalido` e o motivo é registrado no log. |
| Registro duplicado ou inconsistente | Tratado por linha (reprovado ou revisão manual), sem interromper o lote. |
| API do MVP fora do ar ou rejeitando o envio | Até 3 tentativas com intervalo de 2 s; se falhar, o prestador é registrado como `FALHA_INTEGRACAO` no log e o fluxo continua com os demais. |
| Reenvio do mesmo prestador | O backend faz inserção/atualização por `id_externo` (idempotente), então reprocessar um lote não duplica registros. |

Nenhuma falha é silenciosa: todas terminam em uma linha de log.

## 8. Como executar

### 8.1 Backend

Pré-requisitos: Python 3.10 ou superior.

```
cd backend
python -m pip install -r requirements.txt
```

Configure a chave da API e, opcionalmente, o caminho do banco. No Windows PowerShell:

```
$env:SOSDRIVER_API_KEY="sua-chave-local"
$env:SOSDRIVER_DB="sosdriver.db"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Sem `SOSDRIVER_API_KEY`, a API usa uma chave padrão de desenvolvimento (`troque-esta-chave`), que não deve ser usada fora de testes locais.

`backend/prestadores_api.py` define um `APIRouter`, incluído em `backend/main.py`:

```python
from prestadores_api import router
app.include_router(router)
```

O parâmetro `--host 0.0.0.0` é necessário para que o n8n, rodando em contêiner, alcance a API. A documentação interativa fica em `http://localhost:8000/docs`.

### 8.2 n8n

1. Inicie o contêiner (o volume mantém workflows e configurações do n8n):
   ```
   docker run -d --name SOSDriver -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
   ```
2. Acesse `http://localhost:5678` e importe `n8n/sosdriver_triagem_prestadores.json`.
3. Copie o CSV para o diretório de arquivos do n8n, no caminho configurado no nó **Ler lote de cadastros**:
   ```
   docker cp data\cadastros_prestadores.csv SOSDriver:/home/node/.n8n-files/cadastros_prestadores.csv
   ```
4. No nó **Enviar ao MVP**, configure a URL da API acessível a partir do contêiner. No Docker Desktop, use `http://host.docker.internal:8000/prestadores`.
5. Configure o cabeçalho `x-api-key` usando uma credencial segura do n8n, com o mesmo valor de `SOSDRIVER_API_KEY`. O texto `CONFIGURAR_CREDENCIAL_NO_N8N` no JSON é apenas um marcador e não é uma chave válida.
6. Execute o workflow manualmente (**Execute workflow**) e confira a resposta da API e o arquivo de log.

O workflow usa gatilho manual. Portanto, uma pessoa precisa iniciar cada execução.

## 9. Integração com o MVP

- `POST /prestadores`: recebe os cadastros aprovados, autentica pelo cabeçalho `x-api-key` e realiza inserção/atualização no SQLite.
- `GET /prestadores`: lista prestadores ativos e permite filtros por `cidade` e `tipo_servico`. Não expõe telefone.

A integração foi exercitada no ambiente de desenvolvimento: três cadastros aprovados (P001, P002 e P003) foram enviados e confirmados pela API e pelo SQLite. As evidências visuais estão em `docs/evidencias/`.

## 10. Testes

O lote demonstrativo (`data/cadastros_prestadores.csv`) tem oito registros: três aprovados e enviados, três reprovados e dois classificados como `revisao_manual`.

| Cenário | Como reproduzir | Resultado esperado | Situação |
|---|---|---|---|
| Sucesso | Lote de exemplo com a API no ar | P001, P002 e P003 enviados e listados em `GET /prestadores` | Executado |
| Decisão | Mesmo lote | P004 duplicado, P005 documento inválido e P006 vencida (reprovados); P007 e P008 em revisão manual | Executado |
| Integração com o MVP | `GET /prestadores` após o lote | Três prestadores persistidos no SQLite | Executado |
| API fora do ar | Parar o uvicorn e executar | Aprovados registrados como `FALHA_INTEGRACAO`; o fluxo não quebra | Pendente (atualizar após executar) |
| Arquivo ausente | Renomear o CSV e executar | Log "LOTE NAO PROCESSADO" | Pendente (atualizar após executar) |
| Arquivo sem coluna obrigatória | Remover a coluna `email` | Log `lote_invalido` | Pendente (atualizar após executar) |
| Reprocessamento | Executar o lote duas vezes | Sem duplicação em `GET /prestadores` | Pendente (atualizar após executar) |

Cenários marcados como pendentes não devem ser considerados testes concluídos.

## 11. Logs e auditoria

O workflow gera um log TXT por execução (`log_triagem_AAAAMMDDHHMMSS.txt`). A primeira linha é um resumo (total, entregues ao MVP, revisão manual, reprovados, falhas de integração e lotes inválidos), seguida de uma linha por cadastro com horário, identificador externo, documento mascarado, status e motivos. O log não contém telefone, e-mail nem documento completo.

O ambiente utilizado gravava os arquivos dentro do contêiner n8n; como não havia volume Docker persistente para os logs, foi necessário copiá-los manualmente para a pasta local:

```
docker cp SOSDriver:/home/node/.n8n-files/log_triagem_20261119191732.txt .\logs\
```

A pasta `logs/` contém somente exemplos sanitizados, não logs brutos com dados pessoais.

## 12. Segurança e LGPD

- Use somente dados fictícios ou anonimizados no repositório público.
- Não publique arquivos `.env`, chaves, banco SQLite com dados pessoais, CSVs reais ou logs brutos.
- Configure a chave da API por variável de ambiente no backend e por credencial no n8n; confira que o JSON exportado do workflow não contém chave real.
- Minimização de dados: o log usa documento mascarado e não registra contatos; a listagem da API não expõe telefone.
- Restrinja o acesso ao CSV, à API, ao banco e aos logs.
- Defina finalidade, base legal, retenção e controle de acesso conforme as diretrizes do projeto e a LGPD.

O protótipo não deve ser considerado pronto para produção sem as melhorias e testes pendentes descritos neste documento.

## 13. Documentação e entregáveis

- Vídeo de apresentação da solução: https://youtu.be/8FvgLmfFE6k
