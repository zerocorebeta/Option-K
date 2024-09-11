import os
import subprocess
import platform
from functools import lru_cache
import asyncio
from aiohttp import web
from fuzzywuzzy import fuzz
import signal
import configparser
import google.generativeai as genai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from vertexai.generative_models import HarmCategory as VertexHarmCategory
from vertexai.generative_models import HarmBlockThreshold as VertexHarmBlockThreshold
from google.generativeai.types import HarmCategory as GoogleHarmCategory
from google.generativeai.types import HarmBlockThreshold as GoogleHarmBlockThreshold
import argparse
import vertexai
import logging
import re

# Move these global variables outside of the run_server function
config = configparser.ConfigParser()
model = None
vertex_safetysettings = {
    VertexHarmCategory.HARM_CATEGORY_HARASSMENT: VertexHarmBlockThreshold.BLOCK_ONLY_HIGH,
    VertexHarmCategory.HARM_CATEGORY_HATE_SPEECH: VertexHarmBlockThreshold.BLOCK_ONLY_HIGH,
    VertexHarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: VertexHarmBlockThreshold.BLOCK_ONLY_HIGH,
    VertexHarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: VertexHarmBlockThreshold.BLOCK_ONLY_HIGH
}

googleai_safetysettings = {
    GoogleHarmCategory.HARM_CATEGORY_HARASSMENT: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_HATE_SPEECH: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: GoogleHarmBlockThreshold.BLOCK_NONE
}

def create_default_config(config_path):
    config = configparser.ConfigParser()
    config['optionk'] = {
        'port': '8089'
    }
    config['vertexai'] = {
        'enabled': 'false',
        'project': 'my-project',
        'location': 'asia-south1',
        'model': 'gemini-1.5-flash-001'
    }
    config['google_ai_studio'] = {
        'enabled': 'true',
        'api_key': 'YOUR_API_KEY_HERE',
        'model': 'gemini-1.5-flash'
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    # Add helpful comments to the config file
    with open(config_path, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write("# Option-K Configuration File\n\n")
        f.write("# [optionk]\n# port: The port number for the Option-K server\n\n")
        f.write("# [vertexai]\n# enabled: Set to true to use Vertex AI\n# project: Your Google Cloud project ID\n# location: The location of your Vertex AI resources\n# model: The Vertex AI model to use\n\n")
        f.write("# [google_ai_studio]\n# enabled: Set to true to use Google AI Studio\n# api_key: Your Google AI Studio API key\n# model: The Google AI Studio model to use\n\n")
        f.write(content)

def get_config_path(custom_path=None):
    if custom_path:
        return custom_path
    
    if platform.system() == "Windows":
        config_path = os.path.join(os.environ.get('APPDATA'), 'optionk', 'config.ini')
    else:
        config_path = os.path.expanduser('~/.config/optionk/config.ini')
    return config_path

@lru_cache(maxsize=1)
def get_system_info():
    system = platform.system()
    machine = platform.machine()
    if system == "Darwin":
        os_name = "macOS"
        version = platform.mac_ver()[0]
    elif system == "Linux":
        os_name = "Linux"
        try:
            distro = subprocess.check_output(["lsb_release", "-ds"]).decode().strip()
        except:
            distro = "Unknown distribution"
        version = distro
    else:
        os_name = system
        version = platform.version()
    
    return f"{os_name} {version} ({machine})"

async def generate_response_stream(query, command_type, system_info):
    is_git_query = is_git_related_query(query)
    
    if is_git_query:
        system_query = f"""Machine-readable output. You are a Git expert providing git commands that match the query.
        Provide git commands specific to this system.
        Rank suggestions by relevance.
        Explain what each git command does and how it works.
        Output as a numbered list (starts with 0) in the format: <git command> - <explanation>.
        """
    else:
        system_query = f"""Machine-readable output. You are a CLI expert providing {command_type} commands that match the query.
        The user's system is: {system_info}
        Provide commands specific to this system.
        Rank suggestions by relevance.
        Explain what each command does and how it works.
        Output as a numbered list (starts with 0) in the format: <command> - <explanation>."""
    
    full_query = f"{system_query}\n\nquery: {query}\n\nProvide up to 9 commands."
    
    if config.getboolean('vertexai', 'enabled', fallback=False):
        response = model.generate_content(
            contents=full_query,
            generation_config=GenerationConfig(
                max_output_tokens=1024,
                temperature=0,
                top_p=1,
                top_k=1
            ),
            safety_settings=vertex_safetysettings,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
    else:  # Google AI Studio
        response = model.generate_content(
            full_query,
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0,
                top_p=1,
                top_k=1
            ),
            safety_settings=googleai_safetysettings,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            full_response += chunk.text
    
    return full_response

def is_git_related_query(query):
    query = query.lower()
    git_terms = ["git", "commit", "branch", "merge", "pull", "push", "rebase", "stash", "checkout", "clone"]
    url_pattern = re.compile(r'https?://\S+|www\.\S+')

    # Check if any git term is mentioned (allowing for misspellings)
    contains_git_term = any(fuzz.partial_ratio(term, query) > 85 for term in git_terms)

    # Check if 'git' is part of a URL
    urls = url_pattern.findall(query)
    git_in_url = any('git' in url.lower() for url in urls)

    # Check for common download commands
    download_commands = ["curl", "wget"]
    looks_like_download = any(command in query for command in download_commands)

    # Check for context (e.g., "How to use git")
    git_context = re.search(r'\b(use|using|with|in)\s+git\b', query) is not None

    return (contains_git_term or git_context) and not (git_in_url or looks_like_download)

async def get_single_best_result(query, command_type, system_info):
    is_git_query = is_git_related_query(query)
    is_commit_message = "commit" in query and "message" in query
    
    if is_git_query:
        system_query = f"""Machine-readable output. 
        Output with JUST the command to run directly in the command line.
        You are a Git expert providing the single best git command that matches the query.
        """
        if is_commit_message:
            system_query += """
            For commit messages:
            1. Rewrite the commit message to meet Conventional Commits Specification.
            2. Use the block-style commit message format with a single pair of quotes.
            3. Separate the title from the body with a blank line.
            4. Wrap the body text at approximately 72 characters.
            5. Output just the git commit command.
            """
        else:
            system_query += "Output JUST the command to run directly in the command line."

    else:
        system_query = f"""Machine-readable output.
        Output with JUST the command to run directly in the command line.
        You are a CLI expert providing the single best {command_type} command that matches the query.
        The user's system is: {system_info}
        Provide a command specific to this system.
        """
    
    full_query = f"{system_query}\n\nquery: {query}\n\n"
    
    if config.getboolean('vertexai', 'enabled', fallback=False):
        response = model.generate_content(
            [full_query],
            generation_config=GenerationConfig(
                max_output_tokens=500,
                temperature=0,
                top_p=1,
                top_k=1
            ),
            safety_settings=vertex_safetysettings,
            stream=False,
        )
        return response.text.strip('` \t\n\r')
    else:  # Google AI Studio
        response = model.generate_content(
            full_query,
            generation_config=genai.GenerationConfig(
                max_output_tokens=100,
                temperature=0,
                top_p=1,
                top_k=1
            ),
            safety_settings=googleai_safetysettings,
        )
        return response.text.strip('` \t\n\r')

async def handle_generate(request):
    data = await request.json()
    query = data['query']
    system_info = get_system_info()
    response = await generate_response_stream(query, "CLI", system_info)
    return web.json_response({'response': response})

async def handle_quick_suggest(request):
    data = await request.json()
    query = data['query']
    system_info = get_system_info()
    result = await get_single_best_result(query, "CLI", system_info)
    return web.json_response({'result': result})

async def shutdown(app):
    print("Shutting down...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.get_event_loop().stop()

def signal_handler(signame):
    print(f"Received signal {signame}. Initiating shutdown...")
    asyncio.create_task(shutdown(None))

def parse_arguments():
    parser = argparse.ArgumentParser(description="Option-K Server")
    parser.add_argument('--config', help='Path to custom config file')
    return parser.parse_args()

def run_server():
    global config, model  # Add this line to use global variables

    args = parse_arguments()
    
    config_path = get_config_path(args.config)
    if not os.path.exists(config_path):
        create_default_config(config_path)
        print(f"Created default configuration file at: {config_path}")
    else:
        print(f"Using configuration file: {config_path}")
    
    config.read(config_path)

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Check configuration and initialize AI model
    try:
        if config.getboolean('vertexai', 'enabled', fallback=False):
            vertexai.init(project=config.get('vertexai', 'project'), location=config.get('vertexai', 'location'))
            model = GenerativeModel(config.get('vertexai', 'model'))
            logging.info("Initialized Vertex AI model")
        elif config.getboolean('google_ai_studio', 'enabled', fallback=False):
            genai.configure(api_key=config.get('google_ai_studio', 'api_key'))
            model = genai.GenerativeModel(config.get('google_ai_studio', 'model'))
            logging.info("Initialized Google AI Studio model")
        else:
            raise ValueError("No AI service is enabled in the configuration")
        
        # Test API
        test_query = "Hello, world!"
        test_result = asyncio.run(get_single_best_result(test_query, "CLI", get_system_info()))
        logging.info(f"API test successful. Response: {test_result}")
    except Exception as e:
        logging.error(f"Error initializing AI model: {str(e)}")
        return

    app = web.Application()
    app.router.add_post('/generate', handle_generate)
    app.router.add_post('/quick_suggest', handle_quick_suggest)
    
    # Set up signal handlers
    for signame in ('SIGINT', 'SIGTERM'):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda: signal_handler(signame)
        )

    port = int(config.get('optionk', 'port'))
    host = 'localhost'
    
    if platform.system() == "Darwin":
        # macOS specific configuration
        logging.info(f"Starting server on http://{host}:{port}")
        web.run_app(app, port=port, host=host)
    elif platform.system() == "Linux":
        # Linux (systemd) specific configuration
        socket_path = '/run/zerocoretwo/server.sock'
        logging.info(f"Starting server on Unix socket: {socket_path}")
        web.run_app(app, port=port, host=host, path=socket_path)
    else:
        # Default configuration
        logging.info(f"Starting server on http://{host}:{port}")
        web.run_app(app, port=port, host=host)

if __name__ == '__main__':
    run_server()