import os
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import typer
import tomllib
import questionary
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="ROTA Data Management CLI - Visão Computacional")
REGISTRY_PATH = Path(__file__).parent.absolute()
CONFIG_FILE = REGISTRY_PATH / "config.toml"

DEFAULT_CONFIG = {
    "projeto": "Projeto-Base",
    "engenheiro": os.getlogin(),
    "hardware_ingest": "Workstation-Default",
    "metodo_storage": "DVC-SSH-MergerFS"
}

def load_config():
    if not CONFIG_FILE.exists():
        content = "[defaults]\n"
        for k, v in DEFAULT_CONFIG.items():
            content += f'{k} = "{v}"\n'
        CONFIG_FILE.write_text(content, encoding="utf-8")
        return DEFAULT_CONFIG
        
    try:
        with open(CONFIG_FILE, "rb") as f:
            cfg = tomllib.load(f)
            return cfg.get("defaults", DEFAULT_CONFIG)
    except Exception:
        return DEFAULT_CONFIG

config_data = load_config()
console = Console()

def get_dvc_remotes():
    try:
        result = subprocess.run(["dvc", "remote", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        remotes = {}
        for line in lines:
            if not line: continue
            parts = line.split('\t')
            if len(parts) >= 2:
                remotes[parts[0]] = parts[1]
        return remotes
    except subprocess.CalledProcessError:
        return {}

def _remote_label(name: str, url: str) -> str:
    """Retorna label formatado indicando [LOCAL ⚡] ou [SSH 🌐] para o remote."""
    if url.startswith("ssh://"):
        host = url.split("ssh://")[1].split("/")[0]
        return f"{name}  [SSH 🌐  {host}]  — ideal para download por outras máquinas"
    else:
        return f"{name}  [LOCAL ⚡ {url}]  — upload direto, muito mais rápido"

@app.command()
def ingest(
    source: Path = typer.Argument(..., help="Pasta original do dataset"),
    name: str = typer.Argument(..., help="Nome base do projeto/dataset"),
    projeto: Optional[str] = typer.Option(None, help="Nome do projeto associado"),
    engenheiro: Optional[str] = typer.Option(None, help="Nome do engenheiro responsável"),
    hardware: Optional[str] = typer.Option(None, help="Hardware utilizado na ingestão"),
    metodo_storage: Optional[str] = typer.Option(None, help="Método de armazenamento"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Tags separadas por vírgula"),
    remote: Optional[str] = typer.Option(None, "--remote", help="Nome do remote DVC de destino"),
    delete: bool = typer.Option(False, "--delete", help="Apaga a origem após o sucesso")
):
    """Indexa dados com timestamp, sobe para o SSH e registra no Git."""
    source = source.absolute()
    if not source.is_dir():
        typer.secho(f"❌ Erro: {source} não é um diretório.", fg="red")
        raise typer.Exit()

    typer.secho("📝 Configure os metadados do Dataset (Pressione Enter para usar o Padrão/Config):", fg="cyan")
    
    # Interação via Questionary
    projeto = projeto or questionary.text("Projeto:", default=config_data.get("projeto", "Nova Rota")).ask()
    engenheiro = engenheiro or questionary.text("Engenheiro responsável:", default=config_data.get("engenheiro", os.getlogin())).ask()
    hardware = hardware or questionary.text("Hardware de Ingestão:", default=config_data.get("hardware_ingest", "Computador-Local")).ask()
    
    storage_choices = ["DVC-SSH-MergerFS", "DVC-Local", "DVC-S3", "DVC-GCloud"]
    default_storage = config_data.get("metodo_storage", "DVC-SSH-MergerFS")
    if default_storage not in storage_choices:
        storage_choices.insert(0, default_storage)
        
    metodo_storage = metodo_storage or questionary.select(
        "Método de Armazenamento:",
        choices=storage_choices,
        default=default_storage
    ).ask()
    
    if not all([projeto, engenheiro, hardware, metodo_storage]):
        typer.secho("❌ Ingresso cancelado.", fg="red")
        raise typer.Exit()
        
    remotes = get_dvc_remotes()
    remote_name = remote
    if not remote_name and remotes:
        remote_choices = [_remote_label(k, v) for k, v in remotes.items()]
        typer.secho("\n💡 Dica: Use LOCAL ⚡ para upload rápido (mesma máquina). Use SSH 🌐 para acessar de outras máquinas.", fg="yellow")
        selected_remote = questionary.select(
            "Selecione o Servidor/HD de destino (Remote do DVC):",
            choices=remote_choices
        ).ask()
        if not selected_remote:
             typer.secho("❌ Ingresso cancelado (Nenhum storage selecionado).", fg="red")
             raise typer.Exit()
        # Extrai o nome real (primeira palavra antes dos espaços)
        remote_name = selected_remote.split("  [")[0].strip()
        
    tags_list = []
    if tags:
        tags_list = [t.strip() for t in tags.split(',')]
    else:
        tags_str = questionary.text("Adicione Tags (opcional, separe por vírgula, ex: noite, chuva):").ask()
        tags_list = [t.strip() for t in tags_str.split(',')] if tags_str else []


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_name = f"{name}_{timestamp}"
    dataset_dest = REGISTRY_PATH / "data" / unique_name
    dvc_dest = REGISTRY_PATH / "data" / f"{unique_name}.dvc"
    meta_dest = dvc_dest.with_suffix(".json")

    typer.echo(f"\n📦 Preparando ingestão: {unique_name}")
    
    # Usamos hardlinks (os.link) para que o processo seja instantâneo e não ocupe o dobro de espaço.
    # Se estiverem em partições de disco diferentes e o hd recusar, recai para cópia clássica.
    typer.echo(f"⚡ Criando Hardlinks do dataset para o registry (Processo instantâneo e Gasto Zero de espaço)...")
    try:
        shutil.copytree(str(source), str(dataset_dest), copy_function=os.link, dirs_exist_ok=True)
    except OSError:
        typer.echo("⚠️ Partições de HD diferentes detectadas. O processo recairá em cópia profunda (pode demorar)...")
        if dataset_dest.exists():
            shutil.rmtree(str(dataset_dest))
        shutil.copytree(str(source), str(dataset_dest), dirs_exist_ok=True)
    
    # Agora sim, adicionamos com DVC o diretório interno
    subprocess.run(["dvc", "add", str(dataset_dest)], check=True)
    
    metadata = {
        "dataset_id": unique_name,
        "projeto": projeto,
        "engenheiro": engenheiro,
        "origem_fisica": str(source),
        "hardware_ingest": hardware,
        "metodo_storage": metodo_storage,
        "dvc_remote": remote_name or "default",
        "tags": tags_list
    }
    meta_dest.write_text(json.dumps(metadata, indent=4, ensure_ascii=False))

    os.chdir(REGISTRY_PATH)
    typer.echo(f"🚀 Enviando para o Storage Central ({remote_name or 'padrao'})...")
    if remote_name:
        subprocess.run(["dvc", "push", "-r", remote_name, str(dvc_dest)], check=True)
    else:
        subprocess.run(["dvc", "push", str(dvc_dest)], check=True)
    
    subprocess.run(["git", "add", str(dvc_dest), str(meta_dest)], check=True)
    subprocess.run(["git", "commit", "-m", f"feat: add dataset {unique_name}"], check=True)

    if delete:
        if typer.confirm(f"⚠️ Confirmar exclusão da origem {source}?"):
            shutil.rmtree(source)
            subprocess.run(["dvc", "gc", "-w", "-f"], check=True)

    typer.secho(f"✨ Dataset {unique_name} registrado!", fg="cyan")

@app.command()
def list_data(
    query: Optional[str] = typer.Argument(None, help="Busca por nome ou data"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filtra datasets que contêm a tag específica")
):
    """Exibe todos os datasets e onde estão salvos."""
    files = list((REGISTRY_PATH / "data").glob("*.dvc"))
    table = Table(title="📦 Datasets Registrados")
    table.add_column("Dataset ID", style="cyan", no_wrap=True)
    table.add_column("Data Criação", style="magenta")
    table.add_column("Onde Está (Remote / IP)", style="green")
    
    remotes = get_dvc_remotes()
    found_any = False
    
    for f in sorted(files, reverse=True):
        if not query or query.lower() in f.stem.lower():
            parts = f.stem.rsplit('_', 2)
            if len(parts) >= 2 and len(parts[1]) == 8:
                p_date = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"
            else:
                p_date = "N/A"
                
            storage_loc = "Desconhecido"
            json_file = f.with_suffix(".json")
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as meta_f:
                        meta = json.load(meta_f)
                        remote_name = meta.get("dvc_remote", "Padrão")
                        url = remotes.get(remote_name, "")
                        if url.startswith("ssh://"):
                            ip_part = url.split("ssh://")[1].split("/")[0]
                            storage_loc = f"{remote_name} ({ip_part})"
                        else:
                            storage_loc = f"{remote_name}"
                            
                        # Extra check para tags
                        if tag:
                            ds_tags = [t.lower() for t in meta.get("tags", [])]
                            if tag.lower() not in ds_tags:
                                continue
                                
                except Exception:
                    # Falhou leitura, se filtro por tag estava ativo, omitir
                    if tag: continue
                    pass
                    
            table.add_row(f.stem, p_date, storage_loc)
            found_any = True
            
    if not found_any:
        console.print("[yellow]🔍 Nenhum dataset encontrado.[/yellow]")
    else:
        console.print(table)

@app.command()
def list_storages():
    """Lista todos os HDs cadastrados no DVC e verifica o espaço livre por SSH."""
    remotes = get_dvc_remotes()
    if not remotes:
        console.print("[yellow]📦 Nenhum storage cadastrado. Use o menu para Configurar Novo Storage/HD.[/yellow]")
        return
        
    table = Table(title="🖥️  Servidores / HDs Conectados")
    table.add_column("Nome / Apelido", style="cyan", bold=True, no_wrap=True)
    table.add_column("Tipo", style="blue", no_wrap=True)
    table.add_column("Caminho", style="magenta")
    table.add_column("Espaço Disponível", style="green")
    
    typer.echo("🔍 Consultando espaço em disco...")
    
    for name, url in remotes.items():
        free_space = "N/A"
        tipo = "SSH 🌐" if url.startswith("ssh://") else "LOCAL ⚡"
        if url.startswith("ssh://"):
            try:
                parts = url[6:].split("/", 1)
                host_part = parts[0]
                path_part = "/" + (parts[1] if len(parts) > 1 else "")
                ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host_part, f"df -h '{path_part}' | tail -n 1"]
                res = subprocess.run(ssh_cmd, capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    cols = res.stdout.strip().split()
                    if len(cols) >= 6:
                        size, used, avail, pcent = cols[1], cols[2], cols[3], cols[4]
                        free_space = f"{avail} Livres (Uso: {pcent} de {size})"
                else:
                    free_space = "Não alcançável"
            except Exception:
                free_space = "Erro de conexão"
        else:
            # Local: usa df diretamente
            try:
                res = subprocess.run(["df", "-h", url], capture_output=True, text=True)
                if res.returncode == 0:
                    cols = res.stdout.strip().split('\n')[-1].split()
                    if len(cols) >= 4:
                        size, used, avail, pcent = cols[1], cols[2], cols[3], cols[4]
                        free_space = f"{avail} Livres (Uso: {pcent} de {size})"
            except Exception:
                free_space = "Erro"
                
        table.add_row(name, tipo, url, free_space)
        
    console.print(table)

@app.command()
def download(name_id: str, target: Path = typer.Argument(..., help="Destino do download")):
    dvc_file = REGISTRY_PATH / "data" / f"{name_id}.dvc"
    json_file = REGISTRY_PATH / "data" / f"{name_id}.json"
    
    if not dvc_file.exists():
        typer.secho(f"❌ Erro: ID '{name_id}' não existe.", fg="red")
        return
        
    remote_arg = []
    if json_file.exists():
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                dvc_remote = meta.get("dvc_remote")
                if dvc_remote and dvc_remote != "default":
                    remote_arg = ["--remote", dvc_remote]
        except Exception:
            pass
            
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dvc", "get", str(REGISTRY_PATH), f"data/{name_id}", "-o", str(target)] + remote_arg, check=True)
    typer.secho(f"✅ Dados em: {target}", fg="green")

@app.command()
def verify():
    """Verifica a integridade do cache e correspondentes no storage remoto."""
    typer.echo("🔍 Verificando a integridade do DVC em relação ao Remote Storage...")
    result = subprocess.run(["dvc", "status", "-c"], capture_output=True, text=True)
    if result.returncode == 0:
        typer.echo(result.stdout)
        typer.secho("✅ Status cache/remote alinhado.", fg="green")
    else:
        typer.echo(result.stdout)
        typer.echo(result.stderr)
        typer.secho("⚠️ Encontrados problemas na integridade do storage. Rode 'dvc push' se necessário.", fg="yellow")

@app.command()
def prefetch(
    query: str = typer.Argument(..., help="Termo de busca para puxar múltiplos datasets"),
    target: Path = typer.Option(Path("treino_ready"), help="Pasta destino onde os dados serão aglomerados")
):
    """Baixa múltiplos datasets de uma vez para preparar ambiente YOLO."""
    files = list((REGISTRY_PATH / "data").glob(f"*{query}*.dvc"))
    if not files:
        typer.secho(f"❌ Nenhum dataset correspondendo a '{query}'.", fg="red")
        return
        
    target.mkdir(parents=True, exist_ok=True)
    typer.echo(f"🚀 Iniciando download de {len(files)} coleções para '{target}'...")
    
    for count, dvc_file in enumerate(files, 1):
        name_id = dvc_file.stem
        typer.echo(f"[{count}/{len(files)}] Baixando {name_id}...")
        
        json_file = dvc_file.with_suffix(".json")
        remote_arg = []
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    dvc_remote = meta.get("dvc_remote")
                    if dvc_remote and dvc_remote != "default":
                        remote_arg = ["--remote", dvc_remote]
            except Exception:
                pass
                
        try:
            subprocess.run(["dvc", "get", str(REGISTRY_PATH), f"data/{name_id}", "-o", str(target / name_id)] + remote_arg, check=True)
        except subprocess.CalledProcessError:
            typer.secho(f"❌ Falha ao baixar {name_id}.", fg="red")
            
    typer.secho("✨ Pre-fetch finalizado para treinamento de modelos!", fg="green")

@app.command()
def remove():
    """Remove interativamente um dataset registrado (Git Rm + Delete Local)."""
    files = list((REGISTRY_PATH / "data").glob("*.dvc"))
    if not files:
        typer.secho("❌ Nenhum dataset encontrado para remover.", fg="red")
        return
        
    choices = [f.stem for f in sorted(files, reverse=True)]
    selected = questionary.select(
        "Selecione o dataset que deseja remover:",
        choices=choices
    ).ask()
    
    if not selected:
        return
        
    confirm = questionary.confirm(f"⚠️  Tem certeza que deseja apagar '{selected}'? (Isso fará git rm dos ponteiros)").ask()
    if confirm:
        dvc_path = REGISTRY_PATH / "data" / f"{selected}.dvc"
        json_path = REGISTRY_PATH / "data" / f"{selected}.json"
        
        subprocess.run(["git", "rm", str(dvc_path), str(json_path)], check=False, capture_output=True)
        if dvc_path.exists(): dvc_path.unlink()
        if json_path.exists(): json_path.unlink()
        
        subprocess.run(["git", "commit", "-m", f"chore: remover dataset {selected}"], check=False, capture_output=True)
        typer.secho(f"✨ Dataset {selected} removido localmente dos ponteiros!", fg="green")
        typer.secho("💡 Dica: Para limpar completamente o arquivo pesado do HD, use a opção 'Escanear e Limpar HD de Dados Órfãos' no Menu Principal.", fg="yellow")
    else:
        typer.echo("Remoção cancelada.")

@app.command()
def clean_storage():
    """Realiza a limpeza profunda (Garbage Collection) conectando ao Storage e expurgando arquivos órfãos."""
    confirm = questionary.confirm(
        "🧹 Isso vai apagar definitivamente todos os dados no servidor remoto que não tem mais referência aqui no Git. Continuar?"
    ).ask()
    if confirm:
        typer.echo("⚡ Rodando Expurgador (DVC Garbage Collection)...")
        remotes = get_dvc_remotes()
        remote_choices = ["Todos os HDs/Storages"] + [f"{k} \t({v})" for k, v in remotes.items()]
        selected_remote = questionary.select("Qual Storage limpar?", choices=remote_choices).ask()
        if not selected_remote: return
        
        if selected_remote == "Todos os HDs/Storages":
            for name in remotes.keys():
                typer.echo(f"🧹 Limpando dados órfãos do storage '{name}'...")
                subprocess.run(["dvc", "gc", "-c", "-f", "-r", name], check=False)
        else:
            name = selected_remote.split(" \t(")[0]
            typer.echo(f"🧹 Limpando dados órfãos do storage '{name}'...")
            subprocess.run(["dvc", "gc", "-c", "-f", "-r", name], check=False)
        typer.secho("✨ Limpeza concluída e espaço físico recuperado!", fg="green")

@app.command()
def move_dataset():
    """Migra um dataset de um Servidor/HD para outro."""
    files = list((REGISTRY_PATH / "data").glob("*.dvc"))
    if not files:
        typer.secho("❌ Nenhum dataset encontrado.", fg="red")
        return
        
    choices = [f.stem for f in sorted(files, reverse=True)]
    dataset_name = questionary.select("Qual Dataset você quer Mover?", choices=choices).ask()
    if not dataset_name: return
    
    remotes = get_dvc_remotes()
    remote_choices = [f"{k} \t({v})" for k, v in remotes.items()]
    selected_target = questionary.select("Para qual NOVO Storage/HD você quer mover?", choices=remote_choices).ask()
    if not selected_target: return
    new_remote = selected_target.split(" \t(")[0]
    
    json_path = REGISTRY_PATH / "data" / f"{dataset_name}.json"
    dvc_path = REGISTRY_PATH / "data" / f"{dataset_name}.dvc"
    
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    old_remote = meta.get("dvc_remote")
    
    if old_remote == new_remote:
        typer.secho(f"⚠️ O dataset já está no Storage {new_remote}.", fg="yellow")
        return
        
    typer.echo("🔄 Fazendo download temporário dos dados do cache (se não houver local)...")
    fetch_args = []
    if old_remote and old_remote != "default":
        fetch_args = ["--remote", old_remote]
        
    try:
        subprocess.run(["dvc", "pull", str(dvc_path)] + fetch_args, check=True)
    except subprocess.CalledProcessError:
         typer.secho("❌ Erro ao puxar dados. Abortando migração.", fg="red")
         return
    
    typer.echo(f"🚀 Enviando para novo servidor ({new_remote})...")
    subprocess.run(["dvc", "push", "-r", new_remote, str(dvc_path)], check=True)
    
    meta["dvc_remote"] = new_remote
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        
    subprocess.run(["git", "add", str(json_path)], check=True)
    subprocess.run(["git", "commit", "-m", f"chore: migrated {dataset_name} to {new_remote}"], check=True)
    
    typer.secho(f"✨ Migração do {dataset_name} concluída para {new_remote}!", fg="green")
    typer.echo("💡 Lembre-se de rodar a 'Limpeza de Órfãos' no HD antigo para limpar o espaço físico definitivamente.")

@app.command()
def dashboard():
    """Abre o painel Web Dashboard (Streamlit)."""
    typer.echo("🚀 Iniciando ROTA Data Registry Dashboard...")
    dashboard_path = REGISTRY_PATH / "dashboard.py"
    if dashboard_path.exists():
        subprocess.run(["uv", "run", "streamlit", "run", str(dashboard_path)])
    else:
        typer.secho("❌ dashboard.py não encontrado.", fg="red")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
        
    typer.secho("\n🚗 Bem-vindo ao ROTA Data Management CLI", fg="cyan", bold=True)
    
    while True:
        action = questionary.select(
            "O que você deseja fazer?",
            choices=[
                questionary.Choice("📦 Ingestão de Dados (Ingest)", "ingest"),
                questionary.Choice("📋 Listar Datasets Registrados", "list_data"),
                questionary.Choice("🖥️  Listar Servidores/HDs Cadastrados", "list_storages"),
                questionary.Choice("📊 Abrir Painel Visual (Dashboard)", "dashboard"),
                questionary.Choice("⬇️  Download de um Dataset", "download"),
                questionary.Choice("📚 Download Múltiplo p/ Treino YOLO (Prefetch)", "prefetch"),
                questionary.Choice("🚚 Migrar Dataset entre HDs", "move_dataset"),
                questionary.Choice("🔍 Verificar Integridade do Storage", "verify"),
                questionary.Choice("🗑️  Remover um Dataset (Git)", "remove"),
                questionary.Choice("🧹 Escanear e Limpar HD de Dados Órfãos", "clean_storage"),
                questionary.Choice("⚙️  Configurar Novo Storage/HD SSH", "setup"),
                questionary.Choice("🚪 Sair", "exit")
            ]
        ).ask()

        if action == "exit" or not action:
            typer.secho("Até logo!", fg="cyan")
            break
            
        elif action == "ingest":
            source = questionary.path("Pasta original do dataset:").ask()
            if not source: continue
            name = questionary.text("Nome base do projeto/dataset:").ask()
            if not name: continue
            delete_opt = questionary.confirm("Deseja apagar a origem após o sucesso?").ask()
            ctx.invoke(ingest, source=Path(source), name=name, delete=delete_opt)
            
        elif action == "list_data":
            query = questionary.text("Buscar por nome (deixe em branco para todos):").ask()
            # Handle user cancelling input with Ctrl+C -> returns None
            if query is None: continue
            ctx.invoke(list_data, query=query if query else None)
            
        elif action == "list_storages":
            ctx.invoke(list_storages)
            
        elif action == "dashboard":
            ctx.invoke(dashboard)
            
        elif action == "download":
            name_id = questionary.text("ID do dataset para baixar:").ask()
            if not name_id: continue
            target = questionary.path("Destino do download:").ask()
            if not target: continue
            ctx.invoke(download, name_id=name_id, target=Path(target))
            
        elif action == "prefetch":
            query = questionary.text("Termo de busca (ex: projeto_X):").ask()
            if not query: continue
            target = questionary.path("Pasta destino:", default="treino_ready").ask()
            if not target: continue
            ctx.invoke(prefetch, query=query, target=Path(target))
            
        elif action == "verify":
            ctx.invoke(verify)
            
        elif action == "remove":
            ctx.invoke(remove)
            
        elif action == "clean_storage":
            ctx.invoke(clean_storage)
            
        elif action == "move_dataset":
            ctx.invoke(move_dataset)
            
        elif action == "setup":
            typer.echo("🚀 Iniciando assistente de configuração de Storage...")
            script_path = REGISTRY_PATH / "setup_storage.sh"
            subprocess.run(["bash", str(script_path)])
            
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    app()
