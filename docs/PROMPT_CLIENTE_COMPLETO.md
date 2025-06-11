# 🤖 Prompt Completo - Sistema RPA Empresarial v2.0

**Template para implementação de sistema RPA customizado baseado em PDD específico**

---

## 📋 Contexto do Projeto

Você é um desenvolvedor Python especialista em automação RPA (Robotic Process Automation) e deve implementar um sistema empresarial completo baseado na arquitetura já estabelecida do Sistema RPA v2.0.

### 🎯 Objetivo
Criar um sistema de automação RPA modular, robusto e em português brasileiro, seguindo exatamente as especificações do **Documento de Definição de Projeto (PDD)** que será fornecido em anexo.

---

## 🏗️ Arquitetura Base Estabelecida

### Estrutura Fundamental (NÃO ALTERAR)
```
sistema_rpa/
├── .vscode/                 # Configurações debug VSCode
├── core/                    # Módulos principais
│   ├── base_rpa.py         # Classe base para todos os RPAs
│   ├── data_manager.py     # Persistência híbrida MongoDB/JSON
│   ├── mongodb_manager.py  # Gerenciamento MongoDB
│   └── notificacoes_simples.py # Sistema de notificações
├── rpa_[nome1]/            # RPA 1 - Conforme PDD
├── rpa_[nome2]/            # RPA 2 - Conforme PDD
├── rpa_[nome3]/            # RPA 3 - Conforme PDD
├── rpa_[nome4]/            # RPA 4 - Conforme PDD
├── workflows/              # Orquestração Temporal.io
├── scripts/                # Utilitários e geradores
├── docs/                   # Documentação completa
├── dashboard_rpa.py        # Interface principal
├── dashboard_notificacoes.py # Configuração de alertas
├── main.py                 # API REST
└── teste_sistema_refatorado.py # Testes
```

### Tecnologias Obrigatórias
- **Python 3.8+** com UV para gerenciamento de dependências
- **Temporal.io** para orquestração robusta de workflows
- **MongoDB/JSON** persistência híbrida (funciona offline)
- **Selenium** para automação web
- **Streamlit** para interfaces web modernas
- **FastAPI** para API REST profissional
- **Google Sheets API** para integração com planilhas

---

## 🤖 Implementação dos RPAs

### Diretrizes Gerais (OBRIGATÓRIAS)

#### 1. Classe Base
Todos os RPAs DEVEM herdar de `BaseRPA` e seguir o padrão:

```python
from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro

class RPA[Nome](BaseRPA):
    def __init__(self):
        super().__init__("RPA [Nome]", usar_browser=True)
    
    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """Método principal - implementar conforme PDD"""
        
        # Notificação automática integrada
        try:
            resultado = await self._processar_dados(parametros)
            
            # Enviar notificação de sucesso
            notificar_sucesso(
                nome_rpa=f"RPA {self.nome_rpa}",
                tempo_execucao=f"{resultado.tempo_execucao:.1f}s",
                resultados=resultado.dados
            )
            
            return resultado
            
        except Exception as e:
            # Enviar notificação de erro
            notificar_erro(
                nome_rpa=f"RPA {self.nome_rpa}",
                erro=str(e),
                detalhes=resultado.mensagem if 'resultado' in locals() else ""
            )
            raise
```

#### 2. Integração Google Sheets
TODOS os RPAs que usam planilhas devem seguir este padrão:

```python
def _conectar_google_sheets(self, caminho_credenciais: str):
    """Conexão padronizada com Google Sheets"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(caminho_credenciais, scopes=scopes)
        self.gc = gspread.authorize(creds)
        
        self.log_progresso("✅ Conectado ao Google Sheets")
        return True
        
    except Exception as e:
        self.log_erro("Erro ao conectar Google Sheets", e)
        return False
```

#### 3. Automação Web Selenium
Padrão obrigatório para automação web:

```python
async def _fazer_login_sistema(self, url: str, usuario: str, senha: str):
    """Login padronizado em sistemas web"""
    try:
        await self.browser.get_page(url)
        
        # Aguardar página carregar
        await self.browser.aguardar_elemento("input[name='usuario']", timeout=30)
        
        # Preencher credenciais
        await self.browser.preencher_campo("input[name='usuario']", usuario)
        await self.browser.preencher_campo("input[name='senha']", senha)
        
        # Fazer login
        await self.browser.clicar_elemento("button[type='submit']")
        
        # Verificar sucesso
        await self.browser.aguardar_elemento("[class*='dashboard']", timeout=10)
        
        self.log_progresso(f"✅ Login realizado com sucesso: {url}")
        return True
        
    except Exception as e:
        self.log_erro(f"Erro no login: {url}", e)
        return False
```

---

## 🌐 Sistema de Interfaces

### Dashboard Principal (dashboard_rpa.py)
DEVE incluir abas obrigatórias:

1. **🏠 Visão Geral**: Status dos RPAs e métricas
2. **⏰ Agendamentos**: Configuração de horários automáticos  
3. **▶️ Execuções Ativas**: RPAs em execução
4. **📊 Histórico**: Todas as execuções passadas
5. **🔔 Notificações**: Link para dashboard de notificações

### API REST (main.py)
Endpoints obrigatórios:

```python
# Status geral
GET /health

# Executar workflow completo conforme PDD
POST /workflow/[nome-do-processo]

# Executar RPAs individuais
POST /rpa/[nome-rpa-1]
POST /rpa/[nome-rpa-2]
POST /rpa/[nome-rpa-3]
POST /rpa/[nome-rpa-4]

# Gerenciar execuções
GET /execucoes
GET /execucoes/{id}
DELETE /execucoes/{id}
```

---

## 📧 Sistema de Notificações (OBRIGATÓRIO)

### Implementação Automática
Todos os RPAs DEVEM ter notificações integradas:

```python
# Notificação de sucesso
notificar_sucesso(
    nome_rpa="Nome do RPA",
    tempo_execucao="30.2s",
    resultados={
        "dados_processados": 150,
        "arquivos_gerados": 3,
        "status": "Concluído com sucesso"
    }
)

# Notificação de erro
notificar_erro(
    nome_rpa="Nome do RPA", 
    erro="Descrição do erro",
    detalhes="Detalhes técnicos para debug"
)
```

### Tipos de Eventos
- ✅ RPA concluído com sucesso
- ❌ RPA com erro/falha
- 🔄 Workflow completo finalizado
- 📊 Dados atualizados (planilhas, sistemas)
- 🎯 Objetivos específicos do PDD atingidos

---

## ⚡ Orquestração Temporal.io

### Workflow Principal
Implementar conforme sequência definida no PDD:

```python
@workflow.defn
class WorkflowPrincipal:
    @workflow.run
    async def executar(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa sequência de RPAs conforme PDD
        """
        
        # RPA 1: [Conforme PDD]
        resultado_rpa1 = await workflow.execute_activity(
            executar_rpa_1,
            parametros["rpa1"],
            start_to_close_timeout=timedelta(hours=1)
        )
        
        # RPA 2: [Conforme PDD] 
        resultado_rpa2 = await workflow.execute_activity(
            executar_rpa_2,
            parametros["rpa2"],
            start_to_close_timeout=timedelta(hours=1)
        )
        
        # Continuar conforme PDD...
```

---

## 🔧 Configurações e Credenciais

### Arquivo .env Obrigatório
```env
# Google Sheets (obrigatório)
GOOGLE_CREDENTIALS_PATH=./gspread-credentials.json

# Sistemas específicos do PDD
SISTEMA1_URL=https://sistema1.empresa.com
SISTEMA1_USERNAME=usuario
SISTEMA1_PASSWORD=senha

SISTEMA2_URL=https://sistema2.empresa.com  
SISTEMA2_USERNAME=usuario
SISTEMA2_PASSWORD=senha

# Gmail API (para notificações)
GMAIL_CREDENTIALS_PATH=./gmail-credentials.json

# MongoDB (opcional)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=sistema_rpa

# Debug
DEBUG_MODE=false
PYTHONPATH=.
```

---

## 🧪 Testes e Validação

### Estrutura de Testes Obrigatória

#### 1. Teste Individual por RPA
```python
# rpa_[nome]/teste_[nome].py
async def testar_rpa_individual():
    """Teste específico do RPA conforme PDD"""
    rpa = RPA[Nome]()
    
    # Dados de teste conforme PDD
    parametros_teste = {
        # Parâmetros específicos do PDD
    }
    
    resultado = await rpa.executar_com_monitoramento(parametros_teste)
    assert resultado.sucesso, f"RPA falhou: {resultado.erro}"
```

#### 2. Teste Sistema Completo
```python
# teste_sistema_refatorado.py
async def testar_workflow_completo():
    """Testa sequência completa conforme PDD"""
    # Implementar teste do workflow completo
```

---

## 📦 Pacotes de Entrega

### Scripts Obrigatórios

#### 1. Geração de Pacote Produção
```bash
# scripts/gerar_pacote_entrega.sh
# Gera pacote completo para cliente final
```

#### 2. Geração de Pacote Desenvolvedor  
```bash
# scripts/gerar_pacote_dev.sh
# Gera pacote com VSCode e debug configurado
```

#### 3. Instalação Automática
```bash
# instalar_sistema.sh (produção)
# instalar_dev.sh (desenvolvimento)
```

---

## 📚 Documentação Obrigatória

### Estrutura docs/
```
docs/
├── MANUAL_SISTEMA_RPA.md          # Manual completo de operação
├── GUIA_INSTALACAO.md            # Instalação todas as plataformas
├── SISTEMA_NOTIFICACOES_COMPLETO.md # Configuração notificações
└── ESPECIFICACAO_PDD.md          # Implementação específica do PDD
```

### Conteúdo Mínimo
- **Manual de operação** completo
- **Guia de instalação** para Windows/Mac/Linux
- **Configuração de notificações** detalhada
- **Especificação técnica** baseada no PDD

---

## 🎯 IMPLEMENTAÇÃO ESPECÍFICA DO PDD

**IMPORTANTE**: As seções abaixo devem ser customizadas baseadas no PDD fornecido:

### 1. Definição dos RPAs
**[PERSONALIZAR CONFORME PDD]**
- RPA 1: [Nome e função específica]
- RPA 2: [Nome e função específica]  
- RPA 3: [Nome e função específica]
- RPA 4: [Nome e função específica]

### 2. Fluxo de Trabalho
**[PERSONALIZAR CONFORME PDD]**
- Sequência de execução dos RPAs
- Dependências entre RPAs
- Critérios de sucesso/falha
- Agendamentos automáticos

### 3. Integrações Específicas
**[PERSONALIZAR CONFORME PDD]**
- Sistemas web específicos
- Planilhas Google Sheets específicas
- APIs externas necessárias
- Formatos de dados específicos

### 4. Regras de Negócio
**[PERSONALIZAR CONFORME PDD]**
- Critérios de processamento
- Validações específicas
- Tratamento de exceções
- Logs e auditoria específicos

---

## ✅ Lista de Verificação

### Implementação Base ✅
- [ ] Estrutura de pastas conforme padrão
- [ ] Classes BaseRPA implementadas
- [ ] Sistema de notificações integrado
- [ ] Dashboards Streamlit funcionais
- [ ] API REST com todos os endpoints
- [ ] Orquestração Temporal.io
- [ ] Configurações VSCode para debug
- [ ] Testes automatizados

### Customização PDD ⚙️
- [ ] RPAs específicos implementados
- [ ] Fluxo de trabalho configurado
- [ ] Integrações específicas funcionais
- [ ] Regras de negócio aplicadas
- [ ] Documentação específica criada
- [ ] Testes específicos do PDD

### Entrega Final 📦
- [ ] Pacote produção gerado
- [ ] Pacote desenvolvedor gerado
- [ ] Documentação completa
- [ ] Manual de instalação
- [ ] Sistema testado e validado

---

## 🚀 Execução

### Comando de Implementação
```
Implemente um Sistema RPA v2.0 completo baseado no PDD anexo, seguindo
rigorosamente esta especificação técnica. Mantenha a arquitetura base
estabelecida e customize apenas as partes específicas indicadas como
[PERSONALIZAR CONFORME PDD].
```

### Entregáveis Esperados
1. **Sistema RPA completo** funcionando
2. **Dashboards web** configurados
3. **API REST** operacional
4. **Notificações automáticas** integradas
5. **Documentação específica** do PDD
6. **Pacotes de instalação** gerados
7. **Testes validados** e funcionais

---

**🎯 Template profissional para replicação do Sistema RPA v2.0 em novos projetos!**

*Desenvolvido para máxima reutilização e customização baseada em PDD específico.*