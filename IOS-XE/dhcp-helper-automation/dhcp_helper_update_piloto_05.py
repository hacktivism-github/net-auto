from netmiko import ConnectHandler
from dotenv import dotenv_values
from hvac import Client 
import sys
import os
import getpass

# Carregar variáveis de ambiente do ficheiro .env
#env_vars = dotenv_values(".env")

# Alternar entre modo interativo e ficheiro .env
USE_INTERACTIVE = False

# Ler credenciais do .env
#USERNAME = env_vars.get("USERNAME") if not USE_INTERACTIVE else None
#PASSWORD = env_vars.get("PASSWORD") if not USE_INTERACTIVE else None

# Modo de simulação (não aplica mudanças)
DRY_RUN = False

# VLAN para teste piloto
# TEST_VLAN = None  # Ex: "10"
# Se TEST_VLAN for None, o script irá aplicar a todas as VLANs
TEST_VLAN = None

# IP do novo DHCP helper
NEW_HELPER = "172.31.20.28"

# Vault config
VAULT_ADDR = "http://127.0.0.1:8200"
VAULT_TOKEN = "<your vault token>"  # temporário, idealmente exportado como variável de ambiente
VAULT_SECRET_PATH = "network"

# Lista de switches
switches = [
    {"host": "<IP Address>", "name": "<Hostname>"},
    {"host": "<IP Address>", "name": "<Hostname>"},
]

# Função para obter credenciais do Vault
def get_credentials():
    # Inicializar o cliente Vault
    client = Client(url="http://127.0.0.1:8200", token=os.getenv("VAULT_TOKEN"))

    # Verifica se autenticou com sucesso
    if not client.is_authenticated():
        raise Exception("Falha na autenticação com o Vault. Verifique o VAULT_TOKEN.")

    # Caminho correto no KV v2 (sem 'secret/data/')
    VAULT_SECRET_PATH = "network"

    try:
        # Lê o segredo no path especificado
        secret = client.secrets.kv.read_secret_version(
            path=VAULT_SECRET_PATH,
            raise_on_deleted_version=True
        )

        # Extrai as credenciais
        username = secret['data']['data'].get('username')
        password = secret['data']['data'].get('password')

        # Validação extra
        if not username or not password:
            raise Exception("Username ou password não definidos no Vault.")

        return username, password

    except Exception as e:
        print(f" Erro ao obter segredos do Vault: {e}")
        raise

def connect_and_update(switch):
    print(f"\nA conectar ao {switch['name']} ({switch['host']})...")

    # Obter credenciais
    username, password = get_credentials()

    # Obter credenciais
    #username = input("Username: ") if USE_INTERACTIVE else USERNAME
    #password = getpass.getpass("Password: ") if USE_INTERACTIVE else PASSWORD

    device = {
        "device_type": "cisco_ios",
        "host": switch["host"],
        "username": username,
        "password": password,
    }

    try:
        net_connect = ConnectHandler(**device)
        net_connect.enable()
        output = net_connect.send_command("show run | section interface Vlan")
    except Exception as e:
        print(f" Falha na conexão ou comando: {e}")
        return

    interfaces = output.split("interface Vlan")
    log_lines = []

    print(f" A Analisar interfaces em {switch['name']}...")
    for section in interfaces[1:]:
        lines = section.strip().splitlines()
        vlan = lines[0].strip()
        if TEST_VLAN and vlan != str(TEST_VLAN):
            continue

        helper_lines = [line for line in lines if "ip helper-address" in line]
        if not helper_lines:
            continue

        current_helpers = [line.split()[-1] for line in helper_lines]
        if NEW_HELPER not in current_helpers:
            print(f"  Interface Vlan{vlan} - helpers atuais: {current_helpers}")
            print(f" {'[DRY-RUN] ' if DRY_RUN else ''}A adicionar helper {NEW_HELPER}...")
            log_lines.append(f"[{switch['name']}] Vlan{vlan}: {current_helpers} -> +{NEW_HELPER}")
            if not DRY_RUN:
                commands = [
                    f"interface Vlan{vlan}",
                    f"ip helper-address {NEW_HELPER}"
                ]
                net_connect.send_config_set(commands)
        else:
            print(f" Interface Vlan{vlan} já contém o helper {NEW_HELPER}")

    net_connect.disconnect()
    print(f" Concluído para {switch['name']}")

    if log_lines:
        with open(f"log_dhcp_helper_{switch['name']}.txt", "w") as f:
            f.write("\n".join(log_lines))

def main():
    for sw in switches:
        connect_and_update(sw)

if __name__ == "__main__":
    main()
