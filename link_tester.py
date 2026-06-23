import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import requests
import threading
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class LinkTesterApp:
    def __init__(self, root):
        """Inicializa a aplicação de teste de links."""
        self.root = root
        self.root.title("Palantir - Verificador de Links M3U")
        self.root.geometry("1000x700")

        # Configurações de aparência
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Listas para armazenar os resultados
        self.valid_links = []
        self.invalid_links = []

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Coluna Esquerda (Entrada e Controles) ---
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ctk.CTkLabel(self.left_frame, text="Diretório com arquivos M3U:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))

        self.path_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.path_frame.pack(fill=tk.X, padx=10, pady=5)
        self.path_entry = ctk.CTkEntry(self.path_frame, placeholder_text="/mnt/VODS")
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.browse_button = ctk.CTkButton(self.path_frame, text="Procurar", width=80, command=self.browse_directory)
        self.browse_button.pack(side=tk.LEFT)

        # Frame de botões
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="Iniciar Verificação", command=self.start_verification, fg_color="#2ecc71", hover_color="#27ae60")
        self.start_button.pack(side=tk.LEFT, expand=True, padx=(0, 5))

        self.clear_button = ctk.CTkButton(self.button_frame, text="Limpar Tudo", command=lambda: self.clear_all(clear_path=True), fg_color="#e74c3c", hover_color="#c0392b")
        self.clear_button.pack(side=tk.LEFT, expand=True, padx=(5, 0))

        # Frame de progresso
        self.progress_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.progress_frame.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self.progress_frame, text="Aguardando início...", anchor="w")
        self.status_label.pack(fill=tk.X)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.set(0)

        # --- Coluna Direita (Resultados) ---
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Resultados Válidos
        ctk.CTkLabel(self.right_frame, text="Links Válidos", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        self.valid_output = ctk.CTkTextbox(self.right_frame, state="disabled", fg_color="#2b2b2b")
        self.valid_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # Resultados Inválidos
        ctk.CTkLabel(self.right_frame, text="Links Inválidos", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        self.invalid_output = ctk.CTkTextbox(self.right_frame, state="disabled", fg_color="#2b2b2b")
        self.invalid_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def browse_directory(self):
        """Abre uma janela para selecionar o diretório."""
        directory = filedialog.askdirectory(title="Selecione a Pasta")
        if directory:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)

    def clear_all(self, clear_path=False):
        """Limpa os campos de saída (e de entrada se solicitado)."""
        if clear_path:
            self.path_entry.delete(0, tk.END)
        self.update_textbox(self.valid_output, "", clear=True)
        self.update_textbox(self.invalid_output, "", clear=True)
        self.valid_links = []
        self.invalid_links = []
        self.progress_bar.set(0)
        self.status_label.configure(text="Aguardando início...")
        self.start_button.configure(state="normal")

    def update_textbox(self, textbox, text, clear=False):
        """Atualiza um CTkTextbox de forma segura."""
        textbox.configure(state="normal")
        if clear:
            textbox.delete("1.0", tk.END)
        if text:
            textbox.insert(tk.END, text)
        textbox.configure(state="disabled")

    def start_verification(self):
        """Inicia o processo de verificação buscando arquivos no diretório."""
        directory = self.path_entry.get().strip()

        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("Aviso", "Por favor, selecione um diretório válido.")
            return

        # Limpa resultados anteriores
        self.clear_all()
        self.start_button.configure(state="disabled")
        self.status_label.configure(text="Buscando arquivos M3U e extraindo links...")

        # Inicia a busca e verificação em uma thread
        thread = threading.Thread(target=self.prepare_and_verify_thread, args=(directory,), daemon=True)
        thread.start()

    def prepare_and_verify_thread(self, directory):
        """Busca arquivos M3U no diretório e extrai links MP4."""
        raw_links = []
        for root_dir, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.m3u', '.m3u8', '.txt')):
                    filepath = os.path.join(root_dir, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('http') and '.mp4' in line.lower():
                                    raw_links.append(line)
                    except Exception as e:
                        print(f"Erro ao ler {filepath}: {e}")
        
        links = list(dict.fromkeys(raw_links)) # Remove duplicatas e preserva ordem
        
        if not links:
            self.root.after(0, lambda: self.status_label.configure(text="Nenhum link .mp4 encontrado."))
            self.root.after(0, lambda: self.start_button.configure(state="normal"))
            return

        self.root.after(0, lambda: self.status_label.configure(text=f"{len(links)} links encontrados. Iniciando testes..."))
        self.verify_links_thread(links)

    def verify_links_thread(self, links):
        """Lógica de verificação que roda em segundo plano."""
        total_links = len(links)
        processed_count = 0

        # Conjuntos para rastrear links únicos (evitar duplicatas)
        seen_valid = set()
        seen_invalid = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_link = {executor.submit(self.test_link, link, headers): link for link in links}

            for future in as_completed(future_to_link):
                link = future_to_link[future]
                try:
                    is_valid, reason = future.result()
                    if is_valid:
                        # Adiciona apenas se não for duplicata
                        if link not in seen_valid:
                            seen_valid.add(link)
                            self.valid_links.append(link)
                            self.root.after(0, self.update_textbox, self.valid_output, f"{link}\n")
                    else:
                        # Adiciona apenas se não for duplicata
                        if link not in seen_invalid:
                            seen_invalid.add(link)
                            self.invalid_links.append(link)
                            self.root.after(0, self.update_textbox, self.invalid_output, f"{link}\n")
                except Exception as exc:
                    # Adiciona apenas se não for duplicata
                    if link not in seen_invalid:
                        seen_invalid.add(link)
                        self.invalid_links.append(link)
                        self.root.after(0, self.update_textbox, self.invalid_output, f"{link}\n")

                processed_count += 1
                progress = processed_count / total_links
                self.root.after(0, self.update_progress, progress, processed_count, total_links)

        self.root.after(0, self.finish_verification)

    def test_link(self, link, headers):
        """Testa se um link de vídeo MP4 está acessível e respondendo."""
        try:
            # stream=True impede o download completo do vídeo, poupando memória e banda
            with requests.get(link, headers=headers, timeout=15, verify=False, allow_redirects=True, stream=True) as response:
                # 200 (OK) ou 206 (Partial Content) indicam sucesso na leitura do arquivo
                if response.status_code in (200, 206):
                    # Lê o primeiro 1KB do stream para garantir que a transferência de dados está fluindo (rodando)
                    _ = next(response.iter_content(chunk_size=1024), b"")
                    return True, "Funcionando"
                else:
                    return False, f"Status Code: {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Timeout (demorou muito para responder)"
        except requests.exceptions.RequestException as e:
            return False, f"Erro de Conexão ({type(e).__name__})"

    def update_progress(self, progress, processed, total):
        """Atualiza a barra de progresso e o status na thread principal."""
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"Verificando {processed}/{total}...")

    def finish_verification(self):
        """Chamado quando a verificação termina."""
        self.status_label.configure(text=f"Verificação concluída! Válidos: {len(self.valid_links)}, Inválidos: {len(self.invalid_links)}")
        self.start_button.configure(state="normal")
        
        # Salva os resultados automaticamente
        self.save_results()

        messagebox.showinfo("Concluído", "A verificação terminou. Os resultados foram salvos em arquivos de texto.")

    def save_results(self):
        """Salva os links válidos e inválidos em arquivos de texto."""
        try:
            # Cria o diretório 'results' se não existir
            results_dir = "results"
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            timestamp = time.strftime("%Y%m%d-%H%M%S")
            valid_filename = os.path.join(results_dir, f"validos_{timestamp}.txt")
            invalid_filename = os.path.join(results_dir, f"invalidos_{timestamp}.txt")

            # Salva links válidos
            with open(valid_filename, "w", encoding="utf-8") as f:
                for link in self.valid_links:
                    f.write(f"{link}\n")

            # Salva links inválidos (apenas o link, sem motivo)
            with open(invalid_filename, "w", encoding="utf-8") as f:
                for link in self.invalid_links:
                    f.write(f"{link}\n")

            self.status_label.configure(text=f"Resultados salvos em '{results_dir}/'")
            print(f"Resultados salvos em '{valid_filename}' e '{invalid_filename}'")

        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar os arquivos de resultado:\n{e}")
            print(f"Erro ao salvar resultados: {e}")


if __name__ == "__main__":
    # Desabilita avisos de SSL para o requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        root = ctk.CTk()
        app = LinkTesterApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Ocorreu um erro fatal: {e}")
        messagebox.showerror("Erro Fatal", f"A aplicação encontrou um erro e precisa ser fechada.\n\nDetalhes: {e}")