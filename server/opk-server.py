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

# Load configuration
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/.optionk/config.ini'))

# Initialize AI model based on configuration
if config.getboolean('vertexai', 'enabled', fallback=False):
    vertexai.init(project=config.get('vertexai', 'project'), location=config.get('vertexai', 'location'))
    model = GenerativeModel(config.get('vertexai', 'model'))
elif config.getboolean('google_ai_studio', 'enabled', fallback=False):
    genai.configure(api_key=config.get('google_ai_studio', 'api_key'))
    model = genai.GenerativeModel(config.get('google_ai_studio', 'model'))
else:
    raise ValueError("No AI service is enabled in the configuration")


vertex_safetysettings = {
    VertexHarmCategory.HARM_CATEGORY_HARASSMENT: VertexHarmBlockThreshold.BLOCK_NONE,
    VertexHarmCategory.HARM_CATEGORY_HATE_SPEECH: VertexHarmBlockThreshold.BLOCK_NONE,
    VertexHarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: VertexHarmBlockThreshold.BLOCK_NONE,
    VertexHarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: VertexHarmBlockThreshold.BLOCK_NONE
}

googleai_safetysettings = {
    GoogleHarmCategory.HARM_CATEGORY_HARASSMENT: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_HATE_SPEECH: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: GoogleHarmBlockThreshold.BLOCK_NONE,
    GoogleHarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: GoogleHarmBlockThreshold.BLOCK_NONE
}

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
    is_git_query = "git" in query.lower()
    
    if is_git_query:
        system_query = f"""Machine-readable output.You are a Git expert providing git commands that match the query.
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

async def get_single_best_result(query, command_type, system_info):
    query = query.lower()
    terms = ["commit", "commits"]
    is_git_query = any(fuzz.partial_ratio(term, query) > 80 for term in terms) and "git" not in query.split("/")
    
    if is_git_query:
        system_query = f"""Machine-readable output. 
        Output with JUST the command to run directly in the command line.
        You are a Git expert providing the single best git command that matches the query.
        """
        if "message" in query:
            system_query += f"\nRewrite the commit message to meet Conventional Commits Specification."
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
                max_output_tokens=100,
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
    return parser.parse_args()

def run_server():
    args = parse_arguments()
    
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
    if platform.system() == "Darwin":
        # macOS specific configuration
        web.run_app(app, port=port, host='localhost')
    elif platform.system() == "Linux":
        # Linux (systemd) specific configuration
        web.run_app(app, port=port, host='localhost', path='/run/zerocoretwo/server.sock')
    else:
        # Default configuration
        web.run_app(app, port=port, host='localhost')

if __name__ == '__main__':
    run_server()