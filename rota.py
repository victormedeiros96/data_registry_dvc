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

@app.command()
def ingest(
    source: Path = typer.Argument(..., help="Pasta original do dataset"),
    name: str = typer.Argument(..., help="Nome base do projeto/dataset"),
    projeto: Optional[str] = typer.Option(None, help="Nome do projeto associado"),
    engenheiro: Optional[str] = typer.Option(None, help="Nome do engenheiro responsável"),
    hardware: Optional[str] = typer.Option(None, help="Hardware utilizado na ingestão"),
    metodo_storage: Optional[str] = typer.Option(None, help="Método de armazenamento"),
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
        "metodo_storage": metodo_storage
    }
    meta_dest.write_text(json.dumps(metadata, indent=4, ensure_ascii=False))

    os.chdir(REGISTRY_PATH)
    typer.echo("🚀 Enviando para o Storage Central (SSH)...")
    subprocess.run(["dvc", "push", str(dvc_dest)], check=True)
    
    subprocess.run(["git", "add", str(dvc_dest), str(meta_dest)], check=True)
    subprocess.run(["git", "commit", "-m", f"feat: add dataset {unique_name}"], check=True)

    if delete:
        if typer.confirm(f"⚠️ Confirmar exclusão da origem {source}?"):
            shutil.rmtree(source)
            subprocess.run(["dvc", "gc", "-w", "-f"], check=True)

    typer.secho(f"✨ Dataset {unique_name} registrado!", fg="cyan")

@app.command()
def list_data(query: Optional[str] = typer.Argument(None, help="Busca por nome ou data")):
    files = list((REGISTRY_PATH / "data").glob("*.dvc"))
    table = Table(title="📦 Datasets Registrados")
    table.add_column("Dataset ID", style="cyan", no_wrap=True)
    table.add_column("Data Criação", style="magenta")
    
    found_any = False
    for f in sorted(files, reverse=True):
        if not query or query.lower() in f.stem.lower():
            parts = f.stem.rsplit('_', 2)
            if len(parts) >= 2 and len(parts[1]) == 8:
                p_date = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"
            else:
                p_date = "N/A"
            table.add_row(f.stem, p_date)
            found_any = True
            
    if not found_any:
        console.print("[yellow]🔍 Nenhum dataset encontrado.[/yellow]")
    else:
        console.print(table)

@app.command()
def download(name_id: str, target: Path = typer.Argument(..., help="Destino do download")):
    dvc_file = REGISTRY_PATH / "data" / f"{name_id}.dvc"
    if not dvc_file.exists():
        typer.secho(f"❌ Erro: ID '{name_id}' não existe.", fg="red")
        return
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dvc", "get", str(REGISTRY_PATH), f"data/{name_id}", "-o", str(target)], check=True)
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
        try:
            subprocess.run(["dvc", "get", str(REGISTRY_PATH), f"data/{name_id}", "-o", str(target / name_id)], check=True)
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
        typer.secho("💡 Dica: Para limpar completamente do 'Storage SSH', rode 'dvc gc -c -r origin' na CLI.", fg="yellow")
    else:
        typer.echo("Remoção cancelada.")

if __name__ == "__main__":
    app()
