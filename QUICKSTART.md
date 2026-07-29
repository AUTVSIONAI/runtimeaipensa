# Quickstart — AIPENSA Runtime Dev Interface

> **Tempo estimado**: 5-10 minutos para ter tudo rodando localmente

---

## ✅ Pré-requisitos

| Ferramenta | Versão | Verificar |
|------------|--------|-----------|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| Git | - | `git --version` |

---

## 🚀 Passo a Passo

### 1. Backend (Python/FastAPI)

```bash
# Entrar no diretório raiz
cd /c/OPENMANUS/OpenManus

# Criar e ativar venv (recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac/Git Bash
# .venv\Scripts\activate   # Windows PowerShell

# Instalar dependências
pip install -r requirements.txt

# Instalar Chromium para browser module (Playwright)
playwright install chromium

# Iniciar servidor API
python -m uvicorn runtime.api.server:app --reload --port 8000
```

**✅ Verificação**: Abra http://localhost:8000/docs → Swagger UI deve carregar

---

### 2. Frontend (Next.js)

```bash
# Novo terminal - entrar no diretório frontend
cd /c/OPENMANUS/OpenManus/frontend

# Instalar dependências
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

**✅ Verificação**: Abra http://localhost:3000 → Dashboard deve carregar

---

## 🔍 Checklist de Validação Rápida

| # | Ação | Esperado |
|---|------|----------|
| 1 | Abrir http://localhost:3000 | Dashboard com ChatPanel central |
| 2 | Verificar header | Badge verde "Live" (WebSocket conectado) |
| 3 | Abrir Sidebar (☰) | 5 categorias de módulos com status |
| 4 | Clicar "New Conversation" | Dialog abre → Criar → Chat funcional |
| 5 | Enviar mensagem no chat | Resposta aparece (streaming simulado) |
| 6 | Abrir aba **Browser** (painel direito) | "Create Session" → URL navega → Screenshot |
| 7 | Abrir aba **Timeline** | Eventos aparecem em tempo real |
| 8 | Abrir aba **Workflow** | Canvas ReactFlow vazio (pronto para nodes) |
| 9 | Abrir aba **Runtime** | Grid de módulos com health indicators |
| 10 | Abrir aba **Debug** | 3 painéis: Logs, State Inspector, Snapshots |
| 11 | Abrir aba **Settings** | 6 tabs funcionais |
| 12 | Abrir aba **Plugins** | Lista vazia + botão "Install Plugin" |

---

## 🐛 Troubleshooting Comum

### Backend não inicia
```bash
# Verificar porta 8000 livre
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Verificar imports Python
python -c "from runtime.api.server import app; print('OK')"
```

### Frontend não compila
```bash
# Limpar cache Next.js
rm -rf .next node_modules
npm install
npm run dev
```

### WebSocket não conecta
- Verificar se backend está rodando na porta 8000
- Verificar CORS no backend: `allow_origins=["http://localhost:3000"]`
- Console do browser → aba Network → WS → verificar handshake

### Módulos mostram "disconnected"
- Backend precisa de `await runtime.start()` no lifespan
- Verificar logs do uvicorn para erros de inicialização

---

## 📁 Estrutura de Arquivos Chave

```
/c/OPENMANUS/OpenManus/
├── runtime/
│   ├── api/
│   │   ├── server.py      # FastAPI app (ENTRY POINT)
│   │   └── models.py      # Pydantic models
│   └── runtime.py         # Runtime class principal
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx      # Dashboard page
│   │   │   └── providers.tsx # QueryClient + WS init
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── chat/
│   │   │   ├── browser/
│   │   │   ├── timeline/
│   │   │   ├── workflow/
│   │   │   ├── runtime/
│   │   │   ├── debug/
│   │   │   ├── settings/
│   │   │   └── plugins/
│   │   ├── stores/           # Zustand stores
│   │   ├── hooks/            # React hooks
│   │   ├── lib/              # API + WS clients
│   │   └── types/runtime.ts  # TypeScript types
│   └── package.json
└── requirements.txt
```

---

## 🔧 Comandos Úteis

### Backend
```bash
# Rodar com logs debug
LOG_LEVEL=DEBUG python -m uvicorn runtime.api.server:app --reload --port 8000

# Testar endpoint específico
curl http://localhost:8000/api/runtime/health
curl http://localhost:8000/api/modules
```

### Frontend
```bash
# Type check
npm run type-check

# Lint
npm run lint

# Build production
npm run build
npm start

# Format code
npm run format
```

### Testes
```bash
# Backend
cd /c/OPENMANUS/OpenManus
pytest tests/ -v

# Frontend
cd /c/OPENMANUS/OpenManus/frontend
npm run test
npm run test:e2e
```

---

## 🎯 Próximos Passos Após Validação

1. **Criar conversa real** → Testar com LLM module (requer API key)
2. **Browser automation** → Gravar fluxo → Replay
3. **Workflow** → Arrastar nodes → Conectar → Executar
4. **Plugins** → Install via registry → Verificar module carrega
5. **Timeline** → Filtrar por correlação → Debug task flow

---

## 📞 Suporte

| Problema | Onde Ver |
|----------|----------|
| Backend errors | Terminal uvicorn + `/api/runtime/health` |
| Frontend errors | Browser Console + Network tab |
| WebSocket issues | Browser Console → WS frames |
| Module not loading | Sidebar status + `/api/modules/{name}/health` |

---

**Pronto!** 🎉 Se tudo passou no checklist, a interface está operacional.