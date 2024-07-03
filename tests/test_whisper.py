# What is this?
## Tests `litellm.transcription` endpoint. Outside litellm module b/c of audio file used in testing (it's ~700kb).

import pytest
import asyncio, time
import aiohttp, traceback
from openai import AsyncOpenAI
import sys, os, dotenv
from typing import Optional
from dotenv import load_dotenv
from litellm.integrations.custom_logger import CustomLogger
import litellm
import logging

# Get the current directory of the file being run
pwd = os.path.dirname(os.path.realpath(__file__))
print(pwd)

file_path = os.path.join(pwd, "gettysburg.wav")

audio_file = open(file_path, "rb")

load_dotenv()

sys.path.insert(
    0, os.path.abspath("../")
)  # Adds the parent directory to the system path
import litellm
from litellm import Router


def test_transcription():
    transcript = litellm.transcription(
        model="whisper-1",
        file=audio_file,
    )
    print(f"transcript: {transcript.model_dump()}")
    print(f"transcript: {transcript._hidden_params}")


# test_transcription()


def test_transcription_azure():
    litellm.set_verbose = True
    transcript = litellm.transcription(
        model="azure/azure-whisper",
        file=audio_file,
        api_base="https://my-endpoint-europe-berri-992.openai.azure.com/",
        api_key=os.getenv("AZURE_EUROPE_API_KEY"),
        api_version="2024-02-15-preview",
    )

    print(f"transcript: {transcript}")
    assert transcript.text is not None
    assert isinstance(transcript.text, str)


# test_transcription_azure()


@pytest.mark.asyncio
async def test_transcription_async_azure():
    transcript = await litellm.atranscription(
        model="azure/azure-whisper",
        file=audio_file,
        api_base="https://my-endpoint-europe-berri-992.openai.azure.com/",
        api_key=os.getenv("AZURE_EUROPE_API_KEY"),
        api_version="2024-02-15-preview",
    )

    assert transcript.text is not None
    assert isinstance(transcript.text, str)


# asyncio.run(test_transcription_async_azure())


@pytest.mark.asyncio
async def test_transcription_async_openai():
    transcript = await litellm.atranscription(
        model="whisper-1",
        file=audio_file,
    )

    assert transcript.text is not None
    assert isinstance(transcript.text, str)


# This file includes the custom callbacks for LiteLLM Proxy
# Once defined, these can be passed in proxy_config.yaml
class MyCustomHandler(CustomLogger):
    def __init__(self):
        self.openai_client = None

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            # init logging config
            print("logging a transcript kwargs: ", kwargs)
            print("openai client=", kwargs.get("client"))
            self.openai_client = kwargs.get("client")

        except:
            pass


proxy_handler_instance = MyCustomHandler()


# Set litellm.callbacks = [proxy_handler_instance] on the proxy
# need to set litellm.callbacks = [proxy_handler_instance] # on the proxy
@pytest.mark.asyncio
async def test_transcription_on_router():
    litellm.set_verbose = True
    litellm.callbacks = [proxy_handler_instance]
    print("\n Testing async transcription on router\n")
    try:
        model_list = [
            {
                "model_name": "whisper",
                "litellm_params": {
                    "model": "whisper-1",
                },
            },
            {
                "model_name": "whisper",
                "litellm_params": {
                    "model": "azure/azure-whisper",
                    "api_base": "https://my-endpoint-europe-berri-992.openai.azure.com/",
                    "api_key": os.getenv("AZURE_EUROPE_API_KEY"),
                    "api_version": "2024-02-15-preview",
                },
            },
        ]

        router = Router(model_list=model_list)

        router_level_clients = []
        for deployment in router.model_list:
            _deployment_openai_client = router._get_client(
                deployment=deployment,
                kwargs={"model": "whisper-1"},
                client_type="async",
            )

            router_level_clients.append(str(_deployment_openai_client))

        response = await router.atranscription(
            model="whisper",
            file=audio_file,
        )
        print(response)

        # PROD Test
        # Ensure we ONLY use OpenAI/Azure client initialized on the router level
        await asyncio.sleep(5)
        print("OpenAI Client used= ", proxy_handler_instance.openai_client)
        print("all router level clients= ", router_level_clients)
        assert proxy_handler_instance.openai_client in router_level_clients
    except Exception as e:
        traceback.print_exc()
        pytest.fail(f"Error occurred: {e}")
