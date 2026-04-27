import subprocess
import os

# Configuración
OUTPUT_FILE = "historial_completo_para_gpt_crm.md"
DIAS_ATRAS = 7  # Cuántos días de historial quieres
EXCLUDE_EXTENSIONS = ['.json', '.lock', '.png', '.jpg', '.svg', '.map'] # Ignorar archivos ruidosos

def run_git_command(command):
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode('utf-8', errors='ignore').strip()
    except subprocess.CalledProcessError as e:
        return ""

def generate_markdown():
    # 1. Obtener los hashes de los commits de los últimos X días
    print(f"Obteniendo commits de los últimos {DIAS_ATRAS} días...")
    hashes = run_git_command(f'git log --since="{DIAS_ATRAS} days ago" --format="%H"').split('\n')
    
    if not hashes or hashes == ['']:
        print("No se encontraron commits en ese rango.")
        return

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Historial de Cambios de Código (Últimos {DIAS_ATRAS} días)\n\n")
        f.write("> Este documento contiene los diffs de código para análisis técnico.\n\n")

        for commit_hash in hashes:
            # Metadatos del commit
            info = run_git_command(f'git show -s --format="## Commit: %h%n**Autor:** %an%n**Fecha:** %ad%n**Mensaje:** %s" {commit_hash}')
            f.write(info + "\n\n")
            
            # Obtener archivos modificados
            files_changed = run_git_command(f'git show --name-only --format="" {commit_hash}').split('\n')
            
            f.write("### Cambios por archivo:\n")
            
            for file_path in files_changed:
                if not file_path: continue
                
                # Filtrar archivos basura (logs, lockfiles, assets)
                _, ext = os.path.splitext(file_path)
                if ext in EXCLUDE_EXTENSIONS:
                    f.write(f"- *{file_path} (Omitido por extensión)*\n")
                    continue
                
                # Obtener el diff específico de ese archivo
                diff = run_git_command(f'git show {commit_hash} -- "{file_path}"')
                
                # Limpiar el diff para quitar encabezados redundantes de git
                lines = diff.split('\n')
                clean_diff = []
                for line in lines:
                    # Ignoramos metadatos técnicos del diff que confunden a veces
                    if line.startswith('index ') or line.startswith('diff --git'):
                        continue
                    clean_diff.append(line)
                
                diff_text = "\n".join(clean_diff)

                if diff_text:
                    f.write(f"#### 📄 `{file_path}`\n")
                    f.write("```diff\n")
                    f.write(diff_text[:3000]) # Limite de seguridad por archivo si es gigante
                    if len(diff_text) > 3000:
                        f.write("\n... (código truncado por longitud) ...")
                    f.write("\n```\n\n")
            
            f.write("---\n\n")

    print(f"¡Listo! Archivo generado: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_markdown()