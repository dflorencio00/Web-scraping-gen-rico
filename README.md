[README.md](https://github.com/user-attachments/files/30622555/README.md)
# Extrator genérico de dados de painéis administrativos web

Template em Python (Playwright) para automatizar a extração de dados de
sistemas administrativos web autenticados — listagens paginadas, abas,
tabelas carregadas via AJAX/DataTables e seções de detalhe que abrem em
nova aba do navegador.

Este script **não** é direcionado a nenhum site específico. Ele foi
generalizado a partir de um caso de uso real e serve como ponto de partida
para adaptar a outros portais com estrutura parecida (formulários com
`<label>` + campo, abas Bootstrap, tabelas dinâmicas).

## Aviso de uso responsável

- O script **não contorna login nenhum**: ele pausa e espera você fazer
  login manualmente no navegador antes de começar a extrair.
- Use apenas em sistemas para os quais você tem autorização de acesso e
  cujos **Termos de Uso** permitem automação/extração de dados, mesmo
  estando autenticado.
- Não inclui, nem deve incluir, credenciais, tokens ou dados extraídos no
  repositório.
- Ajuste o `TARGET_URL` e os seletores para o seu caso — como está, os
  valores são placeholders e não apontam para nenhum sistema real.

## O que o script resolve

- **Rótulo → valor**: encontra um `<label>` pelo texto exato e lê o valor
  do campo associado, cobrindo tanto `<input>`/`<select>`/`<textarea>`
  quanto texto estático (`<p class="form-control-static">`).
- **Ambiguidade de tabelas**: quando a página tem mais de uma tabela e
  colunas com nomes parecidos, localiza a tabela certa exigindo uma
  combinação de cabeçalhos únicos, em vez de pegar a primeira que
  aparecer no HTML.
- **Tabelas via AJAX**: espera a tabela terminar de carregar antes de ler
  cabeçalho/linha, evitando capturar um estado intermediário vazio.
- **Abas Bootstrap**: clica precisamente no link real da aba
  (`a[data-toggle="tab"]`), evitando clicar em elementos que só contêm o
  mesmo texto mas não ativam a aba.
- **Detalhe em nova aba (`target="_blank"`)**: captura a nova página via
  `context.expect_page()` em vez de continuar lendo a página antiga (erro
  comum que resulta em campos sempre vazios).
- **Seções com múltiplos pares chave/valor**: extrai blocos delimitados
  por um título (`<h5>`), somando várias ocorrências quando existem.

## Como usar

1. Instale as dependências:

   ```bash
   pip install playwright pandas openpyxl
   playwright install chromium
   ```

2. Edite `extrair_dados_portal_generico.py`:
   - `TARGET_URL`: URL do sistema.
   - Os textos passados para `pegar_valor_por_rotulo`, `clicar_aba` e
     `extrair_tabela_por_cabecalhos`: troque pelos rótulos/abas/colunas
     reais do seu formulário.
   - O número de colunas esperado na listagem principal (`len(colunas) < 5`)
     e os índices lidos (`colunas[0]`, `colunas[1]`...).

3. Rode:

   ```bash
   python extrair_dados_portal_generico.py
   ```

4. Faça login manualmente na janela do navegador que abrir, navegue até a
   tela de listagem e pressione ENTER no terminal para iniciar a extração.

5. Ao final, os dados são salvos em `dados_extraidos.xlsx` e
   `dados_extraidos.csv`.

## Licença

Sinta-se à vontade para adaptar este template para o seu caso de uso.
