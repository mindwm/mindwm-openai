from mindwm import logger
from mindwm.model.events import IoDocument, LLMAnswer, LLMAnswerEvent, CloudEvent
from mindwm.knfunc.decorators import iodoc, app
from strictjson import strict_json
import os
import ast

model_engine = "gpt-4"

@iodoc
async def mindwm_openai(iodocument: IoDocument, pane_title: str, graph):
    tmux_pane = graph.TmuxPane.match(pane_title)
    iodocs = tmux_pane.match_children_by_rel(graph.TmuxPaneHasIoDocument, graph.IoDocument)          
    sorted_iodocs = sorted(iodocs, key=lambda doc: doc.merged, reverse=True)
    last_iodoc = sorted_iodocs[0]
 
    input_text = f"{iodocument.input}:{last_iodoc.output}"

    answer = strict_json(system_prompt = '', user_prompt = input_text, output_format = {'codesnippet': 'Code snippet', 'description': 'Description'}, llm=llm)
    logger.info(answer)

    codesnippet = answer['codesnippet']
    description = answer['description']
    
    result = LLMAnswer(
      iodoc_uuid = iodocument.uuid,
      codesnippet=codesnippet,
      description=description
    )

    logger.info(f"reply: {result}")
    return result


def llm(system_prompt: str, user_prompt: str) -> str:
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model_engine,
        temperature = 0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content
