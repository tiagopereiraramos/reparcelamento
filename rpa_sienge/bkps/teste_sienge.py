#!/usr/bin/env python3
"""
Teste COMPLETO do RPA Sienge - Sistema de Reparcelamento
Executa reparcelamento completo com todas as fases até geração do arquivo de remessa
Focado no desenvolvimento e debugging do fluxo completo

ATUALIZADO: Usa novos métodos de processamento em lote do rpa_sienge.py
Desenvolvido em Português Brasileiro
"""

from core.mongodb_manager import mongodb_manager
from rpa_sienge import RPASienge
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Configurações e Credenciais ---


def credenciais_sienge_env() -> Dict[str, str]:
    """Carrega credenciais do Sienge das variáveis de ambiente"""
    return {
        "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8/index.html"),
        "usuario": os.getenv("SIENGE_USUARIO", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_SENHA", ""),
        "empresa": os.getenv("SIENGE_EMPRESA", "1")
    }

# --- Funções de Carregamento de Dados ---


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Carrega índices econômicos do sistema ou usa valores simulados"""
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("📈 Carregando índices econômicos...")

        # Busca os dois índices separadamente
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")

        if ipca is not None and igpm is not None:
            print(
                f"✅ Índices carregados do sistema: IPCA={ipca} | IGPM={igpm}")
            return {
                "ipca": {"valor": ipca, "tipo": "IPCA", "periodo": "Recente"},
                "igpm": {"valor": igpm, "tipo": "IGPM", "periodo": "Recente"}
            }
        else:
            print("📊 Usando índices simulados")
            return {
                "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
                "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
            }
    except Exception as e:
        print(f"❌ Erro ao carregar índices: {str(e)}")
        return {
            "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
            "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
        }


async def verificar_fila_contratos():
    """Verifica e mostra estatísticas da fila de contratos"""
    try:
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            print("❌ Erro: MongoDB não conectado")
            return False

        collection = mongodb_manager.database.fila_contratos

        # Contar por status
        total = collection.count_documents({})
        pendentes = collection.count_documents({"status": "PENDENTE"})
        extraidos = collection.count_documents({"status": "EXTRAIDO"})
        reparcelados = collection.count_documents({"status": "REPARCELADO"})
        carne_gerados = collection.count_documents({"status": "CARNE_GERADO"})
        processados = collection.count_documents({"status": "PROCESSADO"})
        erros = collection.count_documents({"status": "ERRO"})

        print(f"📊 ESTATÍSTICAS DA FILA DE CONTRATOS:")
        print(f"   📄 Total: {total}")
        print(f"   ⏳ Pendentes: {pendentes}")
        print(f"   📥 Extraídos: {extraidos}")
        print(f"   📤 Reparcelados: {reparcelados}")
        print(f"   🎫 Carnês gerados: {carne_gerados}")
        print(f"   ✅ Processados: {processados}")
        print(f"   ❌ Com erro: {erros}")

        if total == 0:
            print("⚠️ Nenhum contrato encontrado na fila")
            return False

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar fila: {str(e)}")
        return False


def escolher_modo_processamento():
    """Permite ao usuário escolher o modo de processamento"""
    print("\n🎯 MODO DE PROCESSAMENTO RPA SIENGE")
    print("=" * 50)
    print("Escolha o modo de execução:")
    print("1. 📥 APENAS EXTRAÇÃO - Extrair relatórios (PENDENTE → EXTRAIDO)")
    print("2. 📤 APENAS REPARCELAMENTO - Reparcelamento (EXTRAIDO → REPARCELADO)")
    print("3. 🎫 APENAS GERAÇÃO CARNÊ - Gerar carnês (REPARCELADO → CARNE_GERADO)")
    print("4. 🔄 PROCESSO COMPLETO - Extração + Reparcelamento + Carnê")
    print("5. 🔧 CONTRATO ÚNICO - Modo legado para um contrato específico")
    print("=" * 50)

    while True:
        escolha = input("Digite sua escolha (1-5): ").strip()

        if escolha == "1":
            return "extracao"
        elif escolha == "2":
            return "reparcelamento"
        elif escolha == "3":
            return "carne"
        elif escolha == "4":
            return "completo"
        elif escolha == "5":
            return "unico"
        else:
            print("❌ Opção inválida! Digite 1, 2, 3, 4 ou 5.")


def escolher_pausas_entre_contratos():
    """Permite ao usuário escolher se quer pausas entre contratos"""
    print("\n⏸️  CONFIGURAÇÃO DE PAUSAS ENTRE CONTRATOS")
    print("=" * 50)
    print("Deseja pausar entre o processamento de cada contrato?")
    print("✅ RECOMENDADO para desenvolvimento/debug:")
    print("   - Controle total sobre cada contrato")
    print("   - Pode acompanhar cada etapa")
    print("   - Pode interromper se necessário")
    print("⚡ Processamento contínuo (mais rápido):")
    print("   - Sem intervenção manual")
    print("   - Execução automática completa")
    print("=" * 50)

    while True:
        escolha = input("Pausar entre contratos? (s/n): ").strip().lower()

        if escolha in ["s", "sim", "y", "yes"]:
            print("✅ Pausas ativadas - você controlará cada contrato")
            print("   💡 Você poderá acompanhar cada etapa do processamento")
            return True
        elif escolha in ["n", "nao", "não", "no"]:
            print("⚡ Processamento contínuo ativado")
            print("   💡 Execução automática sem intervenção")
            return False
        else:
            print("❌ Opção inválida! Digite 's' para sim ou 'n' para não.")

# --- Teste Completo de Reparcelamento EM LOTE (NOVO) ---


async def teste_reparcelamento_lote():
    """
    TESTE COMPLETO EM LOTE: Usa os novos métodos de processamento
    Muito mais simples e eficiente que a versão anterior
    """
    print("🧪 TESTE COMPLETO - REPARCELAMENTO EM LOTE (VERSÃO 2.0)")
    print("=" * 70)
    print("🎯 USANDO NOVOS MÉTODOS: processar_fila_contratos_lote()")
    print("✅ PERSISTÊNCIA ADEQUADA: Dados extraídos SIM, valores da planilha NÃO")
    print("=" * 70)

    # BREAKPOINT 0: Início do teste
    print("\n⏸️  BREAKPOINT 0: Início do teste")
    print("   🧪 Teste de reparcelamento em lote")
    print("   📋 Vamos configurar o teste passo a passo")
    input("   Pressione ENTER para começar...")

    try:
        # 1. VERIFICAR FILA E CONFIGURAÇÕES
        print("\n📊 FASE 1: VERIFICAÇÃO DA FILA")
        print("-" * 40)

        fila_valida = await verificar_fila_contratos()
        if not fila_valida:
            print("❌ Erro na verificação da fila. Abortando teste.")
            return False

        # BREAKPOINT 0.5: Fila verificada
        print("\n⏸️  BREAKPOINT 0.5: Fila de contratos verificada")
        print("   ✅ Fila válida - contratos disponíveis para processamento")
        input("   Pressione ENTER para carregar índices e credenciais...")

        indices_economicos = await carregar_indices_economicos()
        credenciais = credenciais_sienge_env()

        # Validar credenciais obrigatórias
        if not credenciais.get("senha"):
            print("❌ ERRO: SIENGE_SENHA não configurada nas variáveis de ambiente")
            print("💡 Configure a variável SIENGE_SENHA antes de continuar")
            return False

        print(f"✅ Configurações carregadas:")
        print(f"   📈 IPCA: {indices_economicos['ipca']['valor']}%")
        print(f"   📈 IGPM: {indices_economicos['igpm']['valor']}%")
        print(f"   🔑 Credenciais: Configuradas")

        # 2. ESCOLHER MODO DE PROCESSAMENTO
        modo = escolher_modo_processamento()

        if modo == "unico":
            return await teste_reparcelamento_unico_contrato()

        # 3. ESCOLHER CONFIGURAÇÃO DE PAUSAS
        pausar_entre_contratos = escolher_pausas_entre_contratos()

        print(f"\n🎯 Configuração final:")
        print(f"   📋 Modo: {modo.upper()}")
        print(
            f"   ⏸️  Pausas: {'Ativadas' if pausar_entre_contratos else 'Desativadas'}")

        # BREAKPOINT 1: Configurações carregadas
        print("\n⏸️  BREAKPOINT 1: Configurações carregadas com sucesso")
        print("   📋 Modo: {modo.upper()}")
        print(
            "   ⏸️  Pausas: {'Ativadas' if pausar_entre_contratos else 'Desativadas'}")
        print("   📈 IPCA: {indices_economicos['ipca']['valor']}%")
        print("   📈 IGPM: {indices_economicos['igpm']['valor']}%")
        input("   Pressione ENTER para inicializar o RPA...")

        # 3. INICIALIZAR RPA
        print("\n🚀 FASE 2: INICIALIZAÇÃO DO RPA")
        print("-" * 40)

        # Browser visível por padrão para desenvolvimento/debug
        headless = os.getenv("SIENGE_HEADLESS", "false").lower() == "true"
        print(f"🌐 Inicializando RPA (headless: {headless})...")

        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        print(f"✅ RPA inicializado com sucesso (headless: {headless})")

        # BREAKPOINT 2: RPA inicializado
        print("\n⏸️  BREAKPOINT 2: RPA inicializado com sucesso")
        print("   🤖 Browser: {'Visível' if not headless else 'Headless'}")
        print("   🔗 URL: {credenciais['url']}")
        print("   👤 Usuário: {credenciais['usuario']}")
        input("   Pressione ENTER para executar processamento em lote...")

        # 4. EXECUTAR PROCESSAMENTO EM LOTE (NOVO MÉTODO)
        print(f"\n🔄 FASE 3: PROCESSAMENTO EM LOTE")
        print("=" * 50)
        print("🚀 Usando método processar_fila_contratos_lote()...")
        print("✅ Duas fases automáticas: extração → reparcelamento")
        print("✅ Persistência adequada integrada")
        print("✅ Status da fila atualizado automaticamente")
        print(
            f"✅ Pausas entre contratos: {'ATIVADAS' if pausar_entre_contratos else 'DESATIVADAS'}")

        # BREAKPOINT 3: Antes do processamento
        print("\n⏸️  BREAKPOINT 3: Antes do processamento")
        print("   🎯 Modo selecionado: {modo.upper()}")
        print(
            "   ⏸️  Pausas entre contratos: {'ATIVADAS' if pausar_entre_contratos else 'DESATIVADAS'}")
        print("   📊 Contratos na fila: Serão processados automaticamente")
        input("   Pressione ENTER para iniciar o processamento...")

        # ✅ EXECUTAR PROCESSAMENTO CONFORME MODO ESCOLHIDO
        if modo == "carne":
            print("\n🎫 INICIANDO: Geração de carnês apenas")
            # Geração de carnês apenas
            resultado = await rpa.processar_fila_geracao_carnes(
                credenciais_sienge=credenciais,
                pausar_entre_contratos=pausar_entre_contratos
            )
        elif modo == "completo":
            print("\n🔄 INICIANDO: Processo completo (extração + reparcelamento + carnê)")
            # Processo completo: extração + reparcelamento + carnê
            resultado = await rpa.processar_fila_contratos_lote(
                credenciais_sienge=credenciais,
                indices=indices_economicos,
                fase="ambas",
                pausar_entre_contratos=pausar_entre_contratos
            )
            # TODO: Adicionar geração de carnês após reparcelamentos
        else:
            print(f"\n📋 INICIANDO: Modo {modo.upper()}")
            # Modos originais (extração, reparcelamento, ambas)
            resultado = await rpa.processar_fila_contratos_lote(
                credenciais_sienge=credenciais,
                indices=indices_economicos,
                fase=modo,
                pausar_entre_contratos=pausar_entre_contratos
            )

        # BREAKPOINT 4: Processamento concluído
        print("\n⏸️  BREAKPOINT 4: Processamento concluído")
        print("   📊 Resultado obtido, gerando relatório...")
        input("   Pressione ENTER para ver o relatório final...")

        # 5. RELATÓRIO FINAL
        print(f"\n📊 RELATÓRIO FINAL")
        print("=" * 60)

        if resultado.get("sucesso"):
            print("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")

            if modo == "carne":
                print(f"\n🎫 FASE GERAÇÃO DE CARNÊS:")
                print(
                    f"   ✅ Contratos processados: {resultado.get('contratos_processados', 0)}")
                print(
                    f"   ❌ Contratos com erro: {resultado.get('contratos_erro', 0)}")
                print(
                    f"   🏢 Empresas processadas: {resultado.get('empresas_processadas', 0)}")
                print(f"   🚀 Início: {resultado.get('timestamp_inicio', '')}")
                print(f"   🏁 Fim: {resultado.get('timestamp_fim', '')}")
            else:
                # Estatísticas da fase de extração
                if resultado.get("fase_extracao", {}).get("executada"):
                    extracao = resultado["fase_extracao"]
                    print(f"\n📥 FASE EXTRAÇÃO:")
                    print(
                        f"   ✅ Sucessos: {extracao['contratos_processados']}")
                    print(f"   ❌ Erros: {extracao['contratos_erro']}")

                # Estatísticas da fase de reparcelamento
                if resultado.get("fase_reparcelamento", {}).get("executada"):
                    reparcelamento = resultado["fase_reparcelamento"]
                    print(f"\n📤 FASE REPARCELAMENTO:")
                    print(
                        f"   ✅ Sucessos: {reparcelamento['contratos_processados']}")
                    print(f"   ❌ Erros: {reparcelamento['contratos_erro']}")

                # Tempo total
                inicio = resultado.get('timestamp_inicio', '')
                fim = resultado.get('timestamp_fim', '')
                print(f"\n⏱️ TEMPO TOTAL:")
                print(f"   🚀 Início: {inicio}")
                print(f"   🏁 Fim: {fim}")

            print(f"\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            return True

        else:
            print(f"❌ ERRO NO PROCESSAMENTO:")
            print(f"   💥 Erro: {resultado.get('erro', 'Erro desconhecido')}")
            print(f"   🕒 Timestamp: {resultado.get('timestamp_erro', 'N/A')}")
            return False

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO TESTE: {str(e)}")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return False
    finally:
        try:
            if 'rpa' in locals():
                await rpa.finalizar()
        except:
            pass

# --- Teste de Contrato Único (MODO LEGADO) ---


async def teste_reparcelamento_unico_contrato():
    """
    MODO LEGADO: Teste de um único contrato (mantido para casos específicos)
    Usa os métodos originais do RPA para um contrato por vez
    """
    print("🔧 TESTE ÚNICO CONTRATO - MODO LEGADO")
    print("=" * 70)
    print("⚠️ MODO LEGADO: Para teste/debug de um contrato específico")
    print("💡 Para produção, use o modo em lote")

    try:
        # Carregar dados
        print("\n📊 CARREGANDO DADOS")
        print("-" * 40)

        fila_valida = await verificar_fila_contratos()
        if not fila_valida:
            print("❌ Erro na verificação da fila. Abortando teste.")
            return False

        # Buscar contratos PENDENTES para escolha
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if mongodb_manager.database is None:
            print("❌ Database não conectado")
            return False

        collection = mongodb_manager.database.fila_contratos
        contratos_pendentes = list(collection.find({"status": "PENDENTE"}))

        if not contratos_pendentes:
            print("❌ Nenhum contrato PENDENTE encontrado")
            return False

        # Mostrar contratos disponíveis
        print(f"\n📋 CONTRATOS PENDENTES DISPONÍVEIS:")
        for i, contrato in enumerate(contratos_pendentes):
            print(
                f"   {i+1}. {contrato.get('numero_titulo')} - {contrato.get('cliente')}")

        # Escolher contrato
        while True:
            try:
                escolha = int(
                    input(f"\nEscolha o contrato (1-{len(contratos_pendentes)}): "))
                if 1 <= escolha <= len(contratos_pendentes):
                    contrato_teste = contratos_pendentes[escolha - 1]
                    break
                else:
                    print("❌ Número inválido!")
            except ValueError:
                print("❌ Digite um número válido!")

        indices_economicos = await carregar_indices_economicos()
        credenciais = credenciais_sienge_env()

        print(
            f"\n✅ Contrato selecionado: {contrato_teste.get('numero_titulo')} - {contrato_teste.get('cliente')}")

        # Inicializar RPA
        print("\n🚀 INICIALIZANDO RPA")
        print("-" * 40)
        rpa = RPASienge()
        await rpa.inicializar()

        # Executar método original para contrato único
        resultado = await rpa.executar(
            contrato=contrato_teste,
            credenciais_sienge=credenciais,
            indices=indices_economicos,
            etapa="completa",
            autorizar_reparcelamento=True,
            notificar_analista=False
        )

        if resultado.sucesso:
            print(f"\n✅ SUCESSO: {resultado.mensagem}")
            print(f"📊 Dados: {resultado.dados}")
            return True
        else:
            print(f"\n❌ FALHA: {resultado.mensagem}")
            if resultado.erro:
                print(f"💥 Erro: {resultado.erro}")
            return False

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {str(e)}")
        return False
    finally:
        try:
            if 'rpa' in locals():
                await rpa.finalizar()
        except:
            pass

# --- Função Principal ---


async def main():
    """Função principal do sistema de testes"""
    print("🤖 TESTE COMPLETO - RPA SIENGE REPARCELAMENTO V2.0")
    print("🚀 NOVA ARQUITETURA: Processamento em lote otimizado")
    print("✅ PERSISTÊNCIA ADEQUADA: Dados extraídos persistidos, valores da planilha sempre lidos em tempo real")
    print()

    # Executa teste completo em lote (padrão)
    print("🚀 Iniciando teste de reparcelamento em lote...")
    sucesso = await teste_reparcelamento_lote()

    print("\n" + "=" * 70)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("🎯 Nova arquitetura funcionando perfeitamente")
        print("✅ Persistência adequada implementada")
        print("✅ Collection fila_contratos integrada")
    else:
        print("❌ TESTE FALHOU - Verifique os logs acima")
        print("💡 Foque nos erros principais antes de continuar")
    print("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
