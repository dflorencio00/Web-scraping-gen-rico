"""
Template genérico de extração de dados de painéis administrativos web,
usando Playwright.

Este script foi generalizado a partir de um caso de uso real (extração de
registros com múltiplas abas, tabelas carregadas via AJAX e uma seção de
detalhe que abre em nova aba do navegador) e não aponta para nenhum site
específico.

IMPORTANTE - use com responsabilidade:
- Rode apenas contra sistemas para os quais você tem autorização/login
  legítimo (o script não contorna autenticação nenhuma; o login é feito
  manualmente por você, na pausa inicial).
- Verifique os Termos de Uso do sistema-alvo antes de automatizar
  extrações em massa, mesmo estando autenticado.
- Ajuste TARGET_URL, os rótulos de campo e os textos de aba/botão abaixo
  para o seu caso real.
"""

import time
import pandas as pd
from playwright.sync_api import sync_playwright

TARGET_URL = "https://exemplo-portal-admin.com.br/"


def pegar_valor_por_rotulo(page, rotulo):
    """
    Busca o <label> com o texto EXATO do rótulo e lê o valor do campo de
    formulário (input/select/textarea) irmão dele. Cobre dois padrões comuns
    em painéis administrativos:
      1. <label>Rótulo</label><input value="...">
      2. <label>Rótulo</label><div><p class="form-control-static">Valor</p></div>

    Usa comparação exata (não "contains") porque em formulários reais é
    comum um rótulo ser substring de outro (ex.: "Status" x "Status (X)"),
    o que faria uma busca por "contains" casar com o campo errado. Também
    ignora elementos escondidos (offsetParent nulo), pois abas fechadas
    costumam continuar no DOM e podem "vazar" valores de outra aba.
    """
    seletor = (
        f"xpath=//label[normalize-space(.)='{rotulo}']"
        f"/following-sibling::*[self::input or self::textarea or self::select][1]"
    )
    try:
        valores = page.eval_on_selector_all(
            seletor,
            "els => els.map(el => el.offsetParent !== null ? el.value : null)"
        )
        for v in valores:
            if v and v.strip():
                return v.strip()
    except:
        pass

    # Fallback: caso o valor apareça como texto simples (não input/select/textarea)
    try:
        valores = page.eval_on_selector_all(
            f"xpath=//*[normalize-space(text())='{rotulo}']/following-sibling::*[1]",
            "els => els.map(el => el.offsetParent !== null ? el.innerText : null)"
        )
        for v in valores:
            if v and v.strip():
                return v.strip()
    except:
        pass

    return ""


def pegar_pares_chave_valor(page, titulo_secao):
    """
    Extrai pares chave/valor de uma subseção demarcada por um <h5> (ex.: um
    bloco "Item principal" com sub-rótulos "Categoria" e "Motivo" dentro
    dele). A seção pode ter uma ou várias linhas ".row" logo abaixo do
    <h5>, até o próximo <h5>; cada linha vira "Categoria - Motivo" e, se
    houver mais de uma, são unidas com "; ".

    Ajuste os nomes 'Categoria'/'Motivo' abaixo para os sub-rótulos reais
    do seu formulário.
    """
    try:
        h5 = page.query_selector(f"xpath=//h5[normalize-space(text())='{titulo_secao}']")
        if not h5 or not h5.is_visible():
            return ""

        pares = h5.evaluate("""
            (h5) => {
                const resultados = [];
                let el = h5.nextElementSibling;
                while (el && el.tagName.toLowerCase() !== 'h5') {
                    if (el.classList.contains('row')) {
                        let chave = '', valor = '';
                        el.querySelectorAll('.form-group').forEach(grupo => {
                            const label = grupo.querySelector('label');
                            const val = grupo.querySelector('.form-control-static');
                            if (!label || !val) return;
                            const texto = label.textContent.trim();
                            const valorTexto = val.textContent.trim();
                            if (texto === 'Categoria') chave = valorTexto;
                            if (texto === 'Motivo') valor = valorTexto;
                        });
                        if (chave || valor) resultados.push(`${chave} - ${valor}`);
                    }
                    el = el.nextElementSibling;
                }
                return resultados;
            }
        """)
        return "; ".join(pares)
    except:
        return ""


def clicar_aba(page, texto_aba):
    """
    Clica com precisão na aba desejada. Prioriza links reais de aba
    Bootstrap (a[data-toggle="tab"]) para evitar casar com o <li> pai ou
    outro elemento qualquer da página que contenha o mesmo texto (o que
    faria o clique não ativar a aba de verdade, deixando o conteúdo
    escondido no DOM e retornando innerText vazio).
    """
    try:
        aba = (
            page.query_selector(f"a[data-toggle='tab']:has-text('{texto_aba}')")
            or page.query_selector(f"a:has-text('{texto_aba}'), button:has-text('{texto_aba}')")
        )
        if aba and aba.is_visible():
            aba.scroll_into_view_if_needed()
            aba.click()
            time.sleep(1.5)
            return True
    except:
        pass
    return False


def extrair_tabela_por_cabecalhos(page, *cabecalhos_obrigatorios, timeout=8000):
    """
    Localiza, entre várias tabelas possivelmente presentes na página, a
    tabela que contém TODOS os cabeçalhos passados em
    `cabecalhos_obrigatorios`, espera ela carregar (útil para tabelas
    alimentadas via AJAX/DataTables) e retorna (cabecalhos, valores da
    primeira linha).

    Usar mais de um cabeçalho obrigatório evita ambiguidade quando duas
    tabelas diferentes compartilham uma mesma coluna (ex.: um identificador
    que aparece tanto na tabela de detalhe quanto numa tabela-resumo).
    """
    partes_seletor = "".join(f":has(th:has-text('{c}'))" for c in cabecalhos_obrigatorios)
    seletor = f"table{partes_seletor}"
    try:
        page.wait_for_selector(f"{seletor} tbody tr", timeout=timeout)
        tabela = page.query_selector(seletor)
        if not tabela:
            return [], []
        cabecalhos = [th.inner_text().strip() for th in tabela.query_selector_all("thead th")]
        primeira_linha = tabela.query_selector("tbody tr")
        valores = (
            [td.inner_text().strip() for td in primeira_linha.query_selector_all("td")]
            if primeira_linha else []
        )
        return cabecalhos, valores
    except Exception:
        return [], []


def extrair_dados():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("Acessando o portal...")
        page.goto(TARGET_URL)

        print("\n--- PAUSA ---")
        input("1. Faça o login e vá até a tela de listagem de registros.\n"
              "2. Quando a tabela com os botões estiver visível, pressione ENTER aqui no terminal...")

        dados_finais = []

        while True:
            page.wait_for_selector("table", timeout=10000)
            linhas = page.query_selector_all("table tbody tr")
            total_linhas = len(linhas)

            print(f"\nEncontrados {total_linhas} registros nesta página.")

            for i in range(total_linhas):
                page.wait_for_selector("table")
                linhas = page.query_selector_all("table tbody tr")
                if i >= len(linhas):
                    break

                linha = linhas[i]
                colunas = linha.query_selector_all("td")
                if len(colunas) < 5:
                    continue

                # Ajuste os índices/nomes conforme as colunas da SUA listagem
                identificador = colunas[0].inner_text().strip()
                nome_registro = colunas[1].inner_text().strip()
                status = colunas[2].inner_text().strip()
                codigo = colunas[3].inner_text().strip()
                categoria = colunas[4].inner_text().strip()

                print(f"[{i+1}/{total_linhas}] Lendo registro: {nome_registro}...")

                # Abrir o detalhe do registro
                btn_detalhe = linha.query_selector("a:has-text('Abrir detalhes')") or linha.query_selector("button:has-text('Abrir detalhes')")
                if btn_detalhe:
                    btn_detalhe.click()
                    time.sleep(2)
                else:
                    continue

                # 1. PAINEL PRINCIPAL DO REGISTRO
                campo_a = pegar_valor_por_rotulo(page, "Campo A")
                campo_b = pegar_valor_por_rotulo(page, "Campo B")

                # Tabela-resumo com um campo extra (ex.: uma coluna que só existe
                # nessa tabela, não na de histórico) - localizada por combinação
                # de cabeçalhos únicos pra não confundir com outra tabela da página.
                campo_extra = ""
                cabecalhos_resumo, valores_resumo = extrair_tabela_por_cabecalhos(
                    page, "Unidade Responsável"
                )
                for idx, cap in enumerate(cabecalhos_resumo):
                    if idx < len(valores_resumo) and cap.strip().lower() == "campo extra":
                        campo_extra = valores_resumo[idx]

                # 2. ABA DE HISTÓRICO (tabela carregada via AJAX)
                data_hora, cidade, local = "", "", ""
                if clicar_aba(page, "Histórico"):
                    cabecalhos, valores = extrair_tabela_por_cabecalhos(
                        page, "Data/Hora", "Local"
                    )
                    print(f"   [DEBUG] Cabeçalhos: {cabecalhos}")
                    print(f"   [DEBUG] Valores:    {valores}")
                    for idx, cap in enumerate(cabecalhos):
                        if idx < len(valores):
                            nome_cap = cap.lower()
                            if "data" in nome_cap or "hora" in nome_cap:
                                data_hora = valores[idx]
                            elif "cidade" in nome_cap or "município" in nome_cap:
                                cidade = valores[idx]
                            elif "local" in nome_cap:
                                local = valores[idx]

                # 3. DETALHE QUE ABRE EM NOVA ABA (target="_blank")
                situacao_detalhe, observacao_detalhe = "", ""
                item_principal, item_secundario = "", ""

                clicar_aba(page, "Painel principal")

                btn_detalhe_extra = page.query_selector("a:has-text('Ver detalhes complementares')") or page.query_selector("button:has-text('Ver detalhes complementares')")
                if btn_detalhe_extra and btn_detalhe_extra.is_visible():
                    # O link abre em uma aba/janela nova (target="_blank"), então
                    # é preciso capturar essa nova página com context.expect_page -
                    # a página original nunca muda e ficaria vazia se lida direto.
                    try:
                        with context.expect_page(timeout=10000) as nova_pagina_info:
                            btn_detalhe_extra.click()
                        pagina_detalhe = nova_pagina_info.value
                        pagina_detalhe.wait_for_load_state()
                        time.sleep(1)

                        situacao_detalhe = pegar_valor_por_rotulo(pagina_detalhe, "Situação")
                        observacao_detalhe = pegar_valor_por_rotulo(pagina_detalhe, "Observações")

                        if clicar_aba(pagina_detalhe, "Seção 1"):
                            item_principal = pegar_pares_chave_valor(pagina_detalhe, "Item principal")
                            item_secundario = pegar_pares_chave_valor(pagina_detalhe, "Itens secundários")

                        pagina_detalhe.close()
                    except Exception as e:
                        print(f"   Aviso ao abrir detalhe complementar: {e}")

                # Salvar registro
                dados_finais.append({
                    "Identificador": identificador,
                    "Registro": nome_registro,
                    "Status": status,
                    "Código": codigo,
                    "Categoria": categoria,
                    "Campo A": campo_a,
                    "Campo B": campo_b,
                    "Campo Extra": campo_extra,
                    "Data/Hora": data_hora,
                    "Cidade": cidade,
                    "Local": local,
                    "Situação (Detalhe)": situacao_detalhe,
                    "Observações (Detalhe)": observacao_detalhe,
                    "Item Principal": item_principal,
                    "Itens Secundários": item_secundario,
                })

                # Voltar para a lista principal
                btn_voltar = page.query_selector("a:has-text('Listagem')")
                if btn_voltar:
                    btn_voltar.click()
                else:
                    page.go_back()

                time.sleep(2)

            # Próxima página da listagem
            btn_proximo = page.query_selector("a:has-text('Próximo'), .pagination .next a")
            if btn_proximo and btn_proximo.is_visible() and "disabled" not in (btn_proximo.get_attribute("class") or ""):
                btn_proximo.click()
                time.sleep(2.5)
            else:
                break

        if dados_finais:
            df = pd.DataFrame(dados_finais)
            df.to_excel("dados_extraidos.xlsx", index=False)
            df.to_csv("dados_extraidos.csv", index=False, encoding="utf-8-sig")
            print("\nSucesso! Planilhas geradas.")

        browser.close()


if __name__ == "__main__":
    extrair_dados()
