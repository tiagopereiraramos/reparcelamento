# Segurança de Credenciais

## Visão Geral

Este documento descreve as melhores práticas para gerenciar credenciais e informações sensíveis no projeto RPA de reparcelamento.

## Arquivo .env

### Localização

O arquivo `.env` contém todas as credenciais e configurações sensíveis. Este arquivo:

- ✅ **DEVE** estar no `.gitignore`
- ✅ **NÃO DEVE** ser commitado no repositório
- ✅ **DEVE** ser mantido localmente em cada ambiente
- ✅ **DEVE** ter permissões restritas (Linux/macOS: `chmod 600 .env`)

### Estrutura

O arquivo `.env` contém:

- Credenciais do Google Sheets (API keys)
- Credenciais do Sienge (usuário/senha)
- Credenciais do Sicredi (usuário/senha por empresa)
- API Key do SendGrid
- Outras configurações sensíveis

### Template

Use o arquivo `env.example` como template. **NUNCA** commite o `.env` com valores reais.

## Boas Práticas

### 1. Nunca Commitar Credenciais

```bash
# Verificar se .env está no .gitignore
cat .gitignore | grep .env

# Verificar se .env não está sendo rastreado
git status | grep .env
```

### 2. Permissões de Arquivo

**Linux/macOS:**
```bash
chmod 600 .env
chmod 600 credentials/*.json
```

**Windows:**
- Configure permissões via Properties > Security
- Restrinja acesso apenas ao usuário necessário

### 3. Backup Seguro

Faça backup das credenciais em local seguro:

```bash
# Criar backup criptografado
tar -czf credenciais_backup_$(date +%Y%m%d).tar.gz .env credentials/
gpg -c credenciais_backup_*.tar.gz
rm credenciais_backup_*.tar.gz
```

### 4. Rotação de Credenciais

- Rotacione senhas periodicamente (recomendado: a cada 90 dias)
- Atualize o arquivo `.env` após rotação
- Teste conexões após atualização

### 5. Variáveis de Ambiente do Sistema

Para produção, considere usar variáveis de ambiente do sistema em vez do arquivo `.env`:

**Linux/macOS:**
```bash
export SIENGE_USUARIO="usuario@sienge.com.br"
export SIENGE_SENHA="senha_segura"
```

**Windows:**
```powershell
[System.Environment]::SetEnvironmentVariable("SIENGE_USUARIO", "usuario@sienge.com.br", "User")
```

## Compartilhamento Seguro

### Entre Desenvolvedores

1. **NUNCA** envie credenciais por e-mail não criptografado
2. Use ferramentas seguras:
   - **1Password** / **LastPass** (gerenciadores de senha)
   - **Signal** / **WhatsApp** (mensagens criptografadas)
   - **GPG** (criptografia de arquivos)

### Para Cliente

1. Forneça credenciais em reunião presencial ou chamada segura
2. Use canal de comunicação seguro
3. Solicite confirmação de recebimento
4. Revise credenciais após entrega

## Arquivos de Credenciais Google

### Localização

Arquivos JSON de credenciais do Google devem estar em:
```
credentials/gspread-*.json
```

### Segurança

- ✅ Adicione `credentials/*.json` ao `.gitignore`
- ✅ Restrinja permissões (Linux/macOS: `chmod 600`)
- ✅ Não compartilhe arquivos JSON publicamente
- ✅ Revogue credenciais comprometidas no Google Cloud Console

### Backup

Faça backup seguro dos arquivos de credenciais:

```bash
# Backup criptografado
gpg -c credentials/gspread-*.json
```

## Troubleshooting

### Problema: Credenciais não funcionam

**Verificações:**
1. Arquivo `.env` existe e está no local correto?
2. Variáveis estão com nomes corretos?
3. Valores não têm espaços extras?
4. Arquivo de credenciais Google existe e é válido?

**Solução:**
```bash
# Validar credenciais
python scripts/validar_credenciais.py
```

### Problema: Credenciais expostas acidentalmente

**Ações imediatas:**
1. **Revogue credenciais comprometidas imediatamente**
2. Gere novas credenciais
3. Atualize o arquivo `.env`
4. Verifique logs do Git para histórico
5. Se commitado, remova do histórico:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

## Checklist de Segurança

- [ ] Arquivo `.env` está no `.gitignore`
- [ ] Arquivo `.env` não está sendo rastreado pelo Git
- [ ] Permissões do `.env` estão restritas (600)
- [ ] Arquivos de credenciais Google estão protegidos
- [ ] Backup seguro das credenciais foi criado
- [ ] Credenciais foram testadas e funcionam
- [ ] Nenhuma credencial está hardcoded no código
- [ ] Documentação não contém credenciais reais

## Contatos de Emergência

Em caso de comprometimento de credenciais:

1. **Google Sheets**: Revogue no Google Cloud Console
2. **Sienge**: Contate suporte para reset de senha
3. **Sicredi**: Contate suporte bancário
4. **SendGrid**: Revogue API key no painel

## Referências

- [OWASP - Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_cryptographic_key)
- [12 Factor App - Config](https://12factor.net/config)
- [GitHub - Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

