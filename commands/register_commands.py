import requests
import yaml
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
APPLICATION_ID = os.environ.get("DISCORD_APPLICATION_ID")

if not TOKEN or not APPLICATION_ID:
    raise ValueError("❌ Error: 'DISCORD_TOKEN' 및 'DISCORD_APPLICATION_ID' 환경 변수가 설정되지 않았습니다.")

URL = f"https://discord.com/api/v9/applications/{APPLICATION_ID}/commands"

with open("discord_commands.yaml", "r") as file:
    yaml_content = file.read()

commands = yaml.safe_load(yaml_content)
headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

# Send the POST request for each command
for command in commands:
    response = requests.post(URL, json=command, headers=headers)
    command_name = command["name"]
    print(f"Command {command_name} created: {response.status_code}")