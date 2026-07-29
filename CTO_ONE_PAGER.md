# AIPENSA Runtime Dev Interface — One-Pager para CTO

## 🎯 O Quê
Interface web interna (não produto final) para **validar, debugar e controlar** o AIPENSA Runtime Engine durante desenvolvimento.

## 🏗️ Arquitetura (2 serviços)

| Serviço | Tech | Porta | Função |
|---------|------|-------|--------|
| **Backend** | FastAPI + Python | 8000 | Expõe 19+ módulos via REST + WebSocket EventBus |
| **Frontend** | Next.js 14 + React 18 | 3000 | Dashboard dev com 6 painéis especializados |

## ✅ Status: **Código 100% Pronto**

| Camada | Status |
|--------|--------|
| Backend API (REST + WS) | ✅ Completo |
| Frontend Core (Next.js, Stores, Hooks) | ✅ Completo |
| Componentes UI (15+ Shadcn/UI) | ✅ Completo |
| Painéis Funcionais (7) | ✅ Completo |
| Tipagem TypeScript/Pydantic | ✅ Completo |
| Integração Runtime → UI | ✅ Mapeada |

## 🚀 Próximos Passos Imediatos (30 min)

```bash
# Backend
cd /c/OPENMANUS/OpenManus
pip install -r requirements.txt
playwright install chromium
python -m uvicorn runtime.api.server:app --reload --port 8000

# Frontend (novo terminal)
cd /c/OPENMANUS/OpenManus/frontend
npm install
npm run dev
```

## 🎛️ O Que a Interface Faz

| Painel | Capacidade |
|--------|------------|
| **Chat** | Conversas com streaming, histórico, context mgmt |
| **Browser** | Sessões Playwright, navegação, actions, screenshots |
| **Timeline** | 150+ eventos em tempo real, correlação/causação, filtros |
| **Workflow** | Visualizador ReactFlow (nodes: agent, tool, condition) |
| **Runtime** | Grid de módulos com health, resource usage charts |
| **Debug** | Logs, state inspector, snapshots (time-travel) |
| **Settings** | 6 tabs: General, Appearance, Connection, Notifications, Advanced, Data |
| **Plugins** | Cards expansíveis, install via registry/URL/file |

## 💡 Por Que Aprovar Agora

1. **ROI Imediato**: Elimina debugging via print/logs — visibilidade total do Runtime
2. **Velocidade**: Validação visual de mudanças no Runtime em segundos
3. **Padronização**: Interface única para toda a equipe (backend + frontend)
4. **Extensível**: Plugin system UI pronto para marketplace interno
5. **Zero Risk**: Ferramenta interna, não exposta a clientes

## 📊 Investimento

| Recurso | Estimativa |
|---------|------------|
| Setup inicial | 30 min (hoje) |
| Validação E2E | 2-4 horas (esta semana) |
| Hardening/Polish | 1 semana (opcional) |
| Manutenção contínua | ~10% de 1 dev |

## 🔐 Segurança
- Apenas localhost (dev)
- Sandbox isolado para execução de código
- CORS restrito a localhost:3000
- Sem segredos no código

---

**Decisão necessária**: ✅ Aprovar para instalação e validação imediata

*Documento completo: `PROJECT_PROPOSAL.md`*