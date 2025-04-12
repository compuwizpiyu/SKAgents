from autogen import Agent, GroupChat, GroupChatManager, ConversableAgent
import autogen
from typing import  Optional, List, Dict
from openai import OpenAIError

class FallbackGroupChatManager(GroupChatManager):
    """
    A modified version of GroupChatManager, which uses the fallback_agent in case a TimeoutError
    or openai.APIConnectionError occurs for any of the agents. For example, if sending a request
    to a model deployed on a Raspberry Pi while the device is offline, the system will instead use
    the fallback_agent ConversableAgent to continue its operation.
    """
    fallback_agent = None
    def __init__(self, fallback_agent: ConversableAgent, *args, **kwargs):

        FallbackGroupChatManager.fallback_agent = fallback_agent
        super().__init__(*args, **kwargs)
        self.replace_reply_func(GroupChatManager.a_run_chat, FallbackGroupChatManager.a_run_chat)

    async def a_run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[GroupChat] = None,
    ):
        """
        Run a group chat asynchronously. Overrides GroupChatManager.a_run_chat method, only
        differing in handling a failed response generation request from the selected speaker.
        """
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = config
        send_introductions = getattr(groupchat, "send_introductions", False)
        silent = getattr(self, "_silent", False)

        if send_introductions:
            # Broadcast the intro
            intro = groupchat.introductions_msg()
            for agent in groupchat.agents:
                await self.a_send(intro, agent, request_reply=False, silent=True)
            # NOTE: We do not also append to groupchat.messages,
            # since groupchat handles its own introductions

        if self.client_cache is not None:
            for a in groupchat.agents:
                a.previous_cache = a.client_cache
                a.client_cache = self.client_cache
        for i in range(groupchat.max_round):
            groupchat.append(message, speaker)

            if self._is_termination_msg(message):
                # The conversation is over
                break

            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    await self.a_send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                speaker = await groupchat.a_select_speaker(speaker, self)
                # let the speaker speak
                # NOTE: uses a fallback agent in case the selected speaker fails to respond
                try:
                    reply = await speaker.a_generate_reply(sender=self)
                except (TimeoutError, OpenAIError):
                    reply = {'content': "The Agent timed out. Falling back to GPT-4...",
                             'name': speaker.name, 'role': 'user'}
                    await speaker.a_send(reply, self, request_reply=False, silent=silent)
                    speaker = self.fallback_agent
                    reply = await speaker.a_generate_reply(sender=self) 
                    if isinstance(reply, dict):
                        reply['content'] = "The Agent timed out. Falling back to GPT-4...\n\n"  + reply['content']
                    elif isinstance(reply, str):
                        reply = "The Agent timed out. Falling back to GPT-4...\n\n"  + reply
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
            # The speaker sends the message without requesting a reply
            await speaker.a_send(reply, self, request_reply=False, silent=silent)
            message = self.last_message(speaker)
        if self.client_cache is not None:
            for a in groupchat.agents:
                a.client_cache = a.previous_cache
                a.previous_cache = None
        return True, None
