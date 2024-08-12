from mindwm import logger
from mindwm.model.events import IoDocument, LLMAnswer, LLMAnswerEvent, CloudEvent
from mindwm.knfunc import iodoc, app
from openai import OpenAI
import os
import re
from uuid import uuid4

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
model_engine = "gpt-4"

@iodoc
async def mindwm_openai(iodocument: IoDocument, pane_title: str, graph):
    tmux_pane = graph.TmuxPane.match(pane_title)
    iodocs = tmux_pane.match_children_by_rel(graph.TmuxPaneHasIoDocument, graph.IoDocument)          
    sorted_iodocs = sorted(iodocs, key=lambda doc: doc.merged, reverse=True)
    last_iodoc = sorted_iodocs[0]
    
    input_text = f"{iodocument.input}:{last_iodoc.output}"
    gpt_answer = client.chat.completions.create(model=model_engine, messages=[{"role": "user", "content": input_text}])
    message_content = gpt_answer.choices[0].message.content

    codesnippet, description = get_codesnippet_with_description(message_content)
    # FIX: If I understand correctly the `codesnipped` field
    # must contain only the text which should be inserted into the terminal
    # as a command to execute and the `description` field should contain
    # a text to show as a notification or command explanation
    # Thus, here we must parse a LLM answer and fill the fields correctly
    result = LLMAnswer(
      iodoc_uuid = iodocument.uuid,
      codesnippet=codesnippet,
      description=description
    )
    logger.info(f"reply: {result}")
    return result

def get_codesnippet_with_description(content):
    code_pattern = r"```(\w+)?\n(.*?)```"
    codesnippets = re.findall(code_pattern, content, re.DOTALL)
    codesnippet = "\n".join([f"Language: {lang.strip() if lang else 'Unknown'}\nCode:\n{code.strip()}" for lang, code in codesnippets])
    description = re.sub(code_pattern, "", content, flags=re.DOTALL).strip()
    
    return codesnippet, description
