# CMS Detector - Detector de CMS com Foco em Drupal

Script Python com interface gráfica para detectar o CMS (Content Management System) usado por websites, com **prioridade especial para detecção de Drupal**.

## 🚀 Características

- **Interface gráfica intuitiva** (tkinter)
- **Detecção robusta de Drupal** com múltiplos métodos:
  - Meta tags Generator
  - Headers HTTP específicos (X-Drupal-Cache)
  - Arquivos característicos (CHANGELOG.txt, drupal.js, etc.)
  - Padrões no código HTML
  - Detecção de versão do Drupal
- **Suporte para outros CMS**: WordPress, Joomla, Magento, Wix, Shopify, Squarespace
- **Flexibilidade de entrada**: aceita domínios em diversos formatos:
  - `example.com`
  - `https://example.com`
  - `http://example.com/path`
  - `www.example.com`
- **Exportação para CSV** dos resultados
- **Interface visual** com cores destacando sites Drupal em verde
- **Varredura em thread separada** (não trava a interface)

## 📋 Requisitos

- Python 3.6+
- requests

## 🔧 Instalação

```bash
# Clone ou baixe o repositório
cd check-cms

# Instale as dependências
pip install -r requirements.txt
```

## 💻 Uso

### Executar o script:

```bash
python cms_detector.py
```

ou

```bash
python3 cms_detector.py
```

### Como usar a interface:

1. **Cole os domínios**: Na área de texto superior, cole uma lista de domínios/URLs (um por linha)
2. **Clique em "Iniciar Varredura"**: O script começará a verificar cada site
3. **Veja os resultados**: Os resultados aparecem na tabela inferior
   - Sites Drupal aparecem com **fundo verde** 🟢
   - Outros CMS aparecem com fundo bege
   - Erros aparecem com fundo rosa
4. **Exportar**: Clique em "Exportar CSV" para salvar os resultados

### Formatos de entrada aceitos:

```
example.com
www.example.com
https://example.com
http://example.com
https://example.com/some/path
```

## 📊 Informações Detectadas

Para cada site, o detector fornece:

- **URL**: O endereço verificado
- **CMS**: Nome do CMS detectado (ou "Desconhecido")
- **Confiança**: Nível de confiança da detecção (Alta/Média/Baixa)
- **Detalhes**: Informações adicionais:
  - Para Drupal: versão detectada e número de indicadores encontrados
  - Para outros CMS: score de confiança

## 🎯 Detecção de Drupal

O script usa múltiplos métodos para garantir detecção precisa de sites Drupal:

1. **Meta Tags**: Busca por `<meta name="Generator" content="Drupal">`
2. **Headers HTTP**: Verifica `X-Drupal-Cache` e `X-Generator`
3. **Arquivos Específicos**:
   - `/CHANGELOG.txt`
   - `/core/CHANGELOG.txt`
   - `/misc/drupal.js`
   - `/core/misc/drupal.js`
   - `/modules/system/system.css`
4. **Padrões HTML**:
   - `Drupal.settings`
   - `sites/default/files`
   - `sites/all/themes`
   - `data-drupal-selector`

## 📁 Exportação

Os resultados podem ser exportados para CSV com as seguintes colunas:
- URL
- CMS
- Confiança
- Detalhes

O arquivo é salvo com timestamp: `cms_results_YYYYMMDD_HHMMSS.csv`

## ⚙️ Configurações Avançadas

Você pode ajustar os timeouts e comportamentos editando a classe `CMSDetector`:

- `self.timeout = 10`: Timeout em segundos para requisições HTTP
- Adicionar novos padrões de detecção
- Adicionar novos CMS

## 🔍 Exemplo de Uso

1. Abra o programa
2. Cole uma lista como:
```
drupal.org
wordpress.org
joomla.org
example.com
mysite.com
```
3. Clique em "Iniciar Varredura"
4. Aguarde a conclusão
5. Sites Drupal aparecerão destacados em verde
6. Exporte os resultados se necessário

## 📝 Notas

- O script tenta primeiro HTTPS, depois HTTP se falhar
- Timeout padrão de 10 segundos por site
- A varredura pode ser interrompida clicando em "Parar"
- Sites inacessíveis aparecem como "Erro" nos resultados

## 🤝 Contribuições

Sinta-se à vontade para contribuir com:
- Novos métodos de detecção
- Suporte para mais CMS
- Melhorias na interface
- Correções de bugs

## 📄 Licença

Este projeto é de código aberto e está disponível sob a licença MIT.
