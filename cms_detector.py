#!/usr/bin/env python3
"""
CMS Detector - Detecta CMS usado por domínios/sites
Foco especial em detecção de Drupal
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import re
import threading
import time
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Tuple, Optional, Callable
import csv
from datetime import datetime


class CMSDetector:
    """Classe para detectar CMS de websites"""

    def __init__(self, max_retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = 10
        self.max_retries = max_retries
        self.retry_delay = 2  # Delay inicial em segundos entre tentativas

    def normalize_url(self, url: str) -> str:
        """Normaliza URL adicionando protocolo se necessário"""
        url = url.strip()
        if not url:
            return None

        # Remove espaços e quebras de linha
        url = url.replace(' ', '')

        # Se não tem protocolo, adiciona https
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return url

    def detect_cms(self, url: str, retry_callback: Optional[Callable] = None) -> Tuple[str, str, Dict]:
        """
        Detecta o CMS usado pelo site com sistema de retry
        Retorna: (cms_name, confidence, details)

        Args:
            url: URL do site a verificar
            retry_callback: Função callback chamada a cada tentativa (recebe attempt, max_retries)
        """
        url = self.normalize_url(url)
        if not url:
            return "Erro", "URL inválida", {}

        last_error = None

        # Tenta até max_retries vezes
        for attempt in range(1, self.max_retries + 1):
            try:
                # Notifica callback da tentativa atual
                if retry_callback:
                    retry_callback(attempt, self.max_retries)

                # Tenta fazer a requisição
                try:
                    response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                    html = response.text
                    headers = response.headers
                except requests.exceptions.SSLError:
                    # Se falhar com HTTPS, tenta HTTP
                    url = url.replace('https://', 'http://')
                    response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                    html = response.text
                    headers = response.headers

                details = {}

                # 1. DETECÇÃO DRUPAL (PRIORIDADE)
                drupal_score = 0
                drupal_indicators = []

                # Verifica meta tag Drupal
                if re.search(r'<meta[^>]*name=["\']Generator["\'][^>]*content=["\'][^"\']*Drupal[^"\']*["\']', html, re.I):
                    drupal_score += 30
                    drupal_indicators.append("Meta Generator tag")

                # Verifica X-Drupal-Cache header
                if 'X-Drupal-Cache' in headers or 'X-Generator' in headers and 'Drupal' in headers.get('X-Generator', ''):
                    drupal_score += 25
                    drupal_indicators.append("Drupal headers")

                # Verifica arquivos específicos do Drupal
                drupal_files = [
                    '/misc/drupal.js',
                    '/CHANGELOG.txt',
                    '/core/CHANGELOG.txt',
                    '/sites/default/files/',
                    '/modules/system/system.css',
                    '/core/misc/drupal.js'
                ]

                for file in drupal_files:
                    try:
                        file_url = urljoin(url, file)
                        file_response = self.session.head(file_url, timeout=5)
                        if file_response.status_code == 200:
                            drupal_score += 15
                            drupal_indicators.append(f"Arquivo encontrado: {file}")
                            break
                    except:
                        pass

                # Verifica padrões no HTML
                drupal_patterns = [
                    r'Drupal\.settings',
                    r'sites/default/files',
                    r'sites/all/themes',
                    r'/core/misc/drupal',
                    r'drupal-[0-9]',
                    r'data-drupal-selector'
                ]

                for pattern in drupal_patterns:
                    if re.search(pattern, html, re.I):
                        drupal_score += 10
                        drupal_indicators.append(f"Padrão encontrado: {pattern}")

                # Se detectou Drupal com boa confiança
                if drupal_score >= 30:
                    confidence = "Alta" if drupal_score >= 50 else "Média"
                    details['indicators'] = drupal_indicators
                    details['score'] = drupal_score

                    # Tenta detectar versão do Drupal
                    version = self._detect_drupal_version(url, html)
                    if version:
                        details['version'] = version

                    return "Drupal", confidence, details

                # 2. DETECÇÃO DE OUTROS CMS

                # WordPress
                if any(pattern in html.lower() for pattern in ['wp-content', 'wp-includes', 'wordpress']):
                    wp_score = 0
                    if re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\']WordPress', html, re.I):
                        wp_score += 30
                    if '/wp-content/' in html:
                        wp_score += 20
                    if '/wp-includes/' in html:
                        wp_score += 20

                    if wp_score >= 30:
                        return "WordPress", "Alta" if wp_score >= 50 else "Média", {'score': wp_score}

                # Joomla
                if any(pattern in html.lower() for pattern in ['joomla', '/components/com_', '/administrator/']):
                    joomla_score = 0
                    if re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\']Joomla', html, re.I):
                        joomla_score += 30
                    if '/components/com_' in html:
                        joomla_score += 20

                    if joomla_score >= 20:
                        return "Joomla", "Média", {'score': joomla_score}

                # Magento
                if any(pattern in html.lower() for pattern in ['magento', 'mage/cookies']):
                    return "Magento", "Média", {}

                # Wix
                if 'wix.com' in html.lower() or 'x-wix' in str(headers).lower():
                    return "Wix", "Alta", {}

                # Shopify
                if 'shopify' in html.lower() or 'cdn.shopify.com' in html.lower():
                    return "Shopify", "Alta", {}

                # Squarespace
                if 'squarespace' in html.lower():
                    return "Squarespace", "Alta", {}

                # Se não detectou nada
                return "Desconhecido", "N/A", {}

            except requests.exceptions.Timeout as e:
                last_error = ("Timeout", str(e))
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Backoff exponencial
                    continue

            except requests.exceptions.ConnectionError as e:
                last_error = ("Conexão falhou", str(e))
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Backoff exponencial
                    continue

            except Exception as e:
                last_error = ("Erro desconhecido", str(e))
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Backoff exponencial
                    continue

        # Se chegou aqui, esgotou todas as tentativas
        if last_error:
            error_type, error_msg = last_error
            details = {'error': error_msg[:100], 'attempts': self.max_retries}
            return "Erro", error_type, details

        return "Erro", "Desconhecido", {}

    def _detect_drupal_version(self, url: str, html: str) -> str:
        """Tenta detectar a versão do Drupal"""
        try:
            # Tenta ler CHANGELOG.txt
            changelog_urls = [
                urljoin(url, '/CHANGELOG.txt'),
                urljoin(url, '/core/CHANGELOG.txt')
            ]

            for changelog_url in changelog_urls:
                try:
                    response = self.session.get(changelog_url, timeout=5)
                    if response.status_code == 200:
                        # Procura por versão no início do arquivo
                        first_lines = '\n'.join(response.text.split('\n')[:10])
                        version_match = re.search(r'Drupal\s+(\d+\.\d+(?:\.\d+)?)', first_lines)
                        if version_match:
                            return version_match.group(1)
                except:
                    continue

            # Tenta detectar pelo HTML
            version_match = re.search(r'Drupal\s+(\d+)', html)
            if version_match:
                return version_match.group(1) + ".x"

        except:
            pass

        return "Não detectada"


class CMSDetectorGUI:
    """Interface gráfica para o detector de CMS"""

    def __init__(self, root):
        self.root = root
        self.root.title("CMS Detector - Foco em Drupal")
        self.root.geometry("1000x700")

        self.detector = CMSDetector()
        self.results = []
        self.is_scanning = False

        self._create_widgets()

    def _create_widgets(self):
        """Cria os widgets da interface"""

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(4, weight=2)

        # Título
        title_label = ttk.Label(main_frame, text="🔍 Detector de CMS - Prioridade: Drupal",
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)

        # Frame de input
        input_frame = ttk.LabelFrame(main_frame, text="Cole os domínios/URLs (um por linha)", padding="5")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        # Área de texto para input
        self.input_text = scrolledtext.ScrolledText(input_frame, height=10, width=80)
        self.input_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.input_text.insert('1.0', "# Exemplos de formatos aceitos:\n"
                                      "# example.com\n"
                                      "# https://example.com\n"
                                      "# http://example.com/path\n"
                                      "# www.example.com\n")

        # Frame de botões
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10, sticky=tk.W)

        self.scan_button = ttk.Button(button_frame, text="🚀 Iniciar Varredura",
                                      command=self._start_scan)
        self.scan_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="⏹️ Parar",
                                      command=self._stop_scan, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        self.clear_button = ttk.Button(button_frame, text="🗑️ Limpar",
                                       command=self._clear_all)
        self.clear_button.grid(row=0, column=2, padx=5)

        self.export_button = ttk.Button(button_frame, text="💾 Exportar CSV",
                                        command=self._export_csv)
        self.export_button.grid(row=0, column=3, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Frame de resultados
        results_frame = ttk.LabelFrame(main_frame, text="Resultados", padding="5")
        results_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # Tabela de resultados
        columns = ('URL', 'CMS', 'Confiança', 'Detalhes')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)

        # Definir cabeçalhos
        self.tree.heading('URL', text='URL/Domínio')
        self.tree.heading('CMS', text='CMS')
        self.tree.heading('Confiança', text='Confiança')
        self.tree.heading('Detalhes', text='Detalhes')

        # Definir larguras
        self.tree.column('URL', width=300)
        self.tree.column('CMS', width=120)
        self.tree.column('Confiança', width=100)
        self.tree.column('Detalhes', width=400)

        # Scrollbar para a tabela
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configurar cores para Drupal
        self.tree.tag_configure('drupal', background='#90EE90')  # Verde claro
        self.tree.tag_configure('other', background='#FFE4B5')    # Bege
        self.tree.tag_configure('error', background='#FFB6C1')    # Rosa claro

        # Status bar
        self.status_label = ttk.Label(main_frame, text="Pronto para escanear",
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def _start_scan(self):
        """Inicia a varredura dos domínios"""
        # Limpar resultados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []

        # Obter lista de URLs
        input_text = self.input_text.get('1.0', tk.END)
        urls = [line.strip() for line in input_text.split('\n')
                if line.strip() and not line.strip().startswith('#')]

        if not urls:
            messagebox.showwarning("Aviso", "Por favor, cole pelo menos um domínio/URL")
            return

        # Atualizar interface
        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()

        # Iniciar thread de varredura
        thread = threading.Thread(target=self._scan_urls, args=(urls,))
        thread.daemon = True
        thread.start()

    def _scan_urls(self, urls: List[str]):
        """Varre URLs em thread separada"""
        drupal_count = 0
        total = len(urls)

        for idx, url in enumerate(urls, 1):
            if not self.is_scanning:
                break

            # Callback para mostrar tentativas de retry
            def update_retry_status(attempt, max_retries):
                if attempt > 1:
                    self.root.after(0, lambda u=url, i=idx, t=total, a=attempt, m=max_retries:
                                  self.status_label.config(
                                      text=f"Verificando {i}/{t}: {u} (Tentativa {a}/{m})"
                                  ))
                else:
                    self.root.after(0, lambda u=url, i=idx, t=total:
                                  self.status_label.config(text=f"Verificando {i}/{t}: {u}"))

            # Detectar CMS com sistema de retry
            cms, confidence, details = self.detector.detect_cms(url, retry_callback=update_retry_status)

            # Formatar detalhes
            details_str = ""
            if cms == "Drupal":
                drupal_count += 1
                if 'version' in details:
                    details_str = f"Versão: {details['version']} | "
                if 'indicators' in details:
                    details_str += f"Indicadores: {len(details['indicators'])}"
            elif cms == "Erro":
                # Mostrar quantas tentativas foram feitas
                if 'attempts' in details:
                    details_str = f"{confidence} (após {details['attempts']} tentativas)"
                else:
                    details_str = confidence
            elif 'score' in details:
                details_str = f"Score: {details['score']}"

            # Adicionar resultado
            result = {
                'url': url,
                'cms': cms,
                'confidence': confidence,
                'details': details_str
            }
            self.results.append(result)

            # Adicionar à tabela
            tag = 'drupal' if cms == "Drupal" else ('error' if cms == "Erro" else 'other')
            self.root.after(0, lambda r=result, t=tag:
                          self.tree.insert('', tk.END,
                                         values=(r['url'], r['cms'], r['confidence'], r['details']),
                                         tags=(t,)))

        # Finalizar
        self.root.after(0, self._finish_scan, drupal_count, total)

    def _finish_scan(self, drupal_count: int, total: int):
        """Finaliza a varredura"""
        self.is_scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()

        # Mostrar resumo
        summary = f"Concluído! {total} sites verificados | "
        summary += f"🟢 {drupal_count} site(s) Drupal encontrado(s)"
        self.status_label.config(text=summary)

        if drupal_count > 0:
            messagebox.showinfo("Drupal Encontrado!",
                              f"🎉 Foram encontrados {drupal_count} site(s) usando Drupal!")

    def _stop_scan(self):
        """Para a varredura"""
        self.is_scanning = False
        self.status_label.config(text="Varredura interrompida pelo usuário")

    def _clear_all(self):
        """Limpa todos os dados"""
        self.input_text.delete('1.0', tk.END)
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.status_label.config(text="Dados limpos. Pronto para nova varredura.")

    def _export_csv(self):
        """Exporta resultados para CSV"""
        if not self.results:
            messagebox.showwarning("Aviso", "Não há resultados para exportar")
            return

        # Selecionar arquivo
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"cms_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['url', 'cms', 'confidence', 'details'])
                writer.writeheader()
                writer.writerows(self.results)

            messagebox.showinfo("Sucesso", f"Resultados exportados para:\n{filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")


def main():
    """Função principal"""
    root = tk.Tk()
    app = CMSDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
