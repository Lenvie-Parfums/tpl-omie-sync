# Sincronização de Estoque — TPL → Omie → Vnda

Automação que lê o estoque do WMS da **TPL**, grava no **Omie** (ERP, Filial 002)
e o Omie propaga automaticamente para a **Vnda** (loja online) via integração nativa.

## Fluxo

```
TPL (WMS)  →  script  →  OMIE (ERP, Filial 002)  →  VNDA (loja)
get/stock       →     IncluirAjusteEstoque            cascata nativa
```

## Estrutura

```
.
├── main.py                        # orquestrador
├── requirements.txt
├── .env.example                   # modelo de variáveis
├── .github/workflows/
│   └── sync-estoque.yml           # agendamento (3x/dia)
└── utils/
    ├── ConsultaTPL.py             # lê estoque da TPL
    └── AtualizaOmie.py            # grava ajuste no Omie
```

## Variáveis de ambiente (Secrets do GitHub)

| Variável | Sistema | Descrição | Status |
|---|---|---|---|
| `TPL_BASE_URL` | TPL | `https://oms.tpl.com.br/api` | OK |
| `TPL_APIKEY` | TPL | chave fornecida pelo comercial TPL | 🔲 pendente |
| `TPL_TOKEN` | TPL | token fornecido pelo comercial TPL | 🔲 pendente |
| `TPL_EMAIL` | TPL | e-mail autorizado | 🔲 confirmar |
| `OMIE_PRODUTO_URL` | Omie | URL ConsultarProduto | OK |
| `OMIE_ESTOQUE_URL` | Omie | URL IncluirAjusteEstoque | OK |
| `APP_KEY_OMIE` | Omie | app_key Filial 002 | OK |
| `APP_SECRET` | Omie | app_secret Filial 002 | OK |

## Como rodar localmente

```bash
pip install -r requirements.txt
cp .env.example .env      # preencha as credenciais
python main.py
```

## Deploy (GitHub Actions)

1. Crie o repositório como **privado** na organização Lenvie-Parfums.
2. Em **Settings → Secrets and variables → Actions**, cadastre os Secrets da tabela acima.
3. Em **Actions**, clique em **Run workflow** para testar manualmente.
4. O agendamento (06h, 12h, 18h SP) assume automaticamente.

## Observações técnicas

### Autenticação TPL
O token do `get/auth` é válido por **1 hora** e não pode ser solicitado mais de uma
vez nesse período (retorna code 400). O script gera o token uma vez no início da
execução e o reutiliza durante toda a rodada. No GitHub Actions isso nunca é problema
pois cada execução é um ambiente novo.

### Campo de estoque
O `get/stock` retorna `balance` (saldo do período) + `resume.balance` (saldo anterior).
O script soma os dois para obter o estoque total atual.

### Locais de estoque no Omie
- `PADRAO` (código `8385256868`) ← recebe o `balance` da TPL
- `AVARIAS` (código `8980234760`) ← recebe o campo `blocked` (sempre 0 por ora,
  a TPL não separa por local; avarias serão tratadas quando houver mapeamento)

## Pendências

- [ ] Obter `TPL_APIKEY`, `TPL_TOKEN` e `TPL_EMAIL` com o comercial da TPL
- [ ] Validar campo de estoque (`balance` + `resume`) com a TPL
- [ ] Testar autenticação e `get/stock` com credenciais reais
- [ ] Confirmar data de transição (quando parar a Estoca e ligar a TPL)
