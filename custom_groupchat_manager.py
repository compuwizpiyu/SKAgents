from dataclasses import dataclass
import json
import sys
from typing import Dict, List, Optional, Union
from autogen import Agent, GroupChat, GroupChatManager
import logging


class CustomGroupChatManager(GroupChatManager):
    """ A chat manager agent that can manage a group chat of multiple agents."""

    def __init__(
        self,
        groupchat: GroupChat,
        name: Optional[str] = "chat_manager",
        # unlimited consecutive auto reply by default
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        system_message: Optional[str] = "Group chat manager.",
        # seed: Optional[int] = 4,
        *args,
        **kwargs,
    ):
        super().__init__(
            groupchat,
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            *args,
            **kwargs,
        )
        self.register_reply(Agent, CustomGroupChatManager.run_chat, config=groupchat, reset_config=GroupChat.reset)
        # self._random = random.Random(seed)

    async def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[GroupChat] = None,
    ) -> Union[str, Dict, None]:
        """Run a group chat."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = config
        for i in range(groupchat.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            groupchat.messages.append(message)
            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                speaker = groupchat.select_speaker(speaker, self)
                # let the speaker speak
                reply = await speaker.a_generate_reply(sender=self)
            except KeyboardInterrupt:
                # let the admin agent speak if interrupted
                if groupchat.admin_name in groupchat.agent_names:
                    # admin agent is one of the participants
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = await speaker.a_generate_reply(sender=self)
                else:
                    # admin agent is not found in the participants
                    raise
            if reply is None:
                break
            
            
            if speaker.name != 'user':
                msg = ""
                msg_type = "message"
                if (not isinstance(reply, str)) and ("tool_calls" in reply or reply["role"] == "tool"):
                    if reply["role"] != "tool":
                        msg = f"'{reply['content']}'"
                else:
                    msg = f"'{reply}'"
                    await self.client_receive_queue.put(json.dumps({'type':msg_type, 'name': speaker.name, 'content': msg}))
                    # await self.client_receive_queue.put(f"{{'type':'{msg_type}', 'name': '{speaker.name}', 'content': {msg}}}")
                # Send message to client
                
            ###!!!!!!!!!!!!!!!!!!!!!!!!!Below commented lines are existing here to future reference!!!!!!!!!!!!!!!!!!!!!!
            # # Send reply to client
            # if speaker.name != 'user':
            #     msg = ""
            #     msg_type = "message"
            #     # if (not isinstance(reply, str)) and ("tool_calls" in reply or reply["role"] == "tool"):
            #     #     if reply["role"] != "tool":
            #     #         c = json.loads(reply["content"])
            #     #         if c["type"] == "image":
            #     #             msg_type = "image"
            #     #             msg = f"'{c['filename']}'"
            #     #             reply["content"] = f"Image of temperature gauge taken. Filename is: {msg}"
            #     #         elif c["type"] == "message":
            #     #             msg = f"'{c['content']}'"
            #     #             reply["content"] = c["content"]
            #     #         elif c["type"] == "list":
            #     #             msg_type = "list"
            #     #             msg = c["content"]
            #     #             reply["content"] = f"List of items: {msg}"
            #     #     else:
            #     #         msg = f"'{reply['content']}'"
            #     # else:
            #     msg = f"'{reply}'"
            #     # Send message to client
            #     await self.client_receive_queue.put(f"{{'type':'{msg_type}', 'name': '{speaker.name}', 'content': {msg}}}")
            # The speaker sends the message without requesting a reply
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None

    def set_queues(self, client_sent_queue, client_receive_queue):
        self.client_sent_queue = client_sent_queue
        self.client_receive_queue = client_receive_queue