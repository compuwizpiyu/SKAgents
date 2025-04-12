import os
import autogen
from custom_user_proxy import CustomUserProxyAgent
from custom_groupchat_manager import CustomGroupChatManager
import asyncio
from dotenv import load_dotenv
from agent_tools import get_customer_details, bing_search
load_dotenv()

llm_config = [
    {
        "model": "GPT4",
        "api_key": os.getenv("APIKEY"),
        "base_url": os.getenv("BASEURL"),
        "api_type": "azure",
        "api_version": "2024-02-01",
        "max_tokens": 2048,
        "stream": False
    }
]

class AutogenChat():
    def __init__(self, chat_id=None, websocket=None):
        self.websocket = websocket
        self.chat_id = chat_id
        self.client_sent_queue = asyncio.Queue()
        self.client_receive_queue = asyncio.Queue()

        #region desc = "AGENTS"
        self.executor = autogen.UserProxyAgent(
            name="executor",
            human_input_mode="NEVER",
            llm_config=False
        )      

        self.user_proxy = CustomUserProxyAgent( 
            name="user",
            human_input_mode="ALWAYS", 
            is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False,
            llm_config=False
        )


        self.information_recommender_agent = autogen.ConversableAgent(
            name="information_recommender_agent",
            system_message="you are a UOB Bank credit card expert employed to help new users find information regarding credit cards offered in UOB Bank Singapore"
                "trigger bing_search function to get the answers"
                "When user provides their current OCBC credit card name and asks for the similar UOB credit card, do the comparison and return the competitive UOB credit card suggestions only"
                "DO NOT CROSS SELL: MEANING DO NOT MARKET PERSONAL LOAN WHEN YOU ARE EMPLOYED TO DO RECOMMEND ONLY CREDIT CARD"
                "STRICTLY DO NOT REPLY MULTIPLE TIMES TO THE USER CONSECUTIVELY. RESPOND BACK TO USER IN SINGLE ANSWER AFTER THOROUGH ANALYSIS OF THE USER QUERY",
            description="You are the UOB Bank Credit Card expert specifically appointed to answer the credit card related question for new user",
            llm_config={"config_list": llm_config},
        )

        self.personalised_credit_recommender_agent = autogen.ConversableAgent(
            name="credit_recommender_agent",
            system_message="you are a UOB Bank credit card expert employed to help existing UOB users find information regarding credit cards offered in UOB Bank Singapore based on their customer profile"
                "trigger bing_search function to get the answers"
                "When UOB user asks for the UOB credit card suggestions only, trigger get_customer_details function by passing 345566767 cust_id variable and use the customer profile data output provided to tailor your recommendations"
                "ONLY IF YOU SUCCEED FINDING THE CUSTOMISED CREDIT CARD, ASSUME USER HAS EXISTING PERSONAL LOAN AND OFFER SOME ATTRACTIVE DISCOUNTS IN INTEREST RATE FOR CREDIT CARD IN YOUR RESPONSE"
                "DO NOT CROSS SELL: MEANING DO NOT MARKET PERSONAL LOAN WHEN YOU ARE EMPLOYED TO RECOMMEND ONLY CREDIT CARD"
                "once you are done with forming the credit card responses, make sure you include the following text at the end: 'You dont need to remember all the things, I will mail all the conversation to your registered email address'"
                "STRICTLY DO NOT REPLY MULTIPLE TIMES TO THE USER CONSECUTIVELY. RESPOND BACK TO USER IN SINGLE ANSWER AFTER THOROUGH ANALYSIS OF THE USER QUERY",
            description="You are the UOB Bank Credit Card expert specifically appointed to answer the personalised credit card questions for existing user",
            llm_config={"config_list": llm_config},
        )


        self.loan_assitant = autogen.ConversableAgent(
            name="loan_assitant",
            system_message="You are the UOB Bank Loan Specialist employed to help users find information regarding loans offered in UOB Bank Singapore"
                    "You help to find the information related to Loans by triggering the bing_search function"
                    "summarize the list of dictionary from bing_search function not more than 50 words"
                    "ONLY When user asks with the intention of comparison, Ensure to include results from both OCBC and UOB websites along with factors you considered for Comparison"
                    "DO NOT REPLY MULTIPLE TIMES TO THE USER CONSECUTIVELY. RESPOND BACK TO USER IN SINGLE ANSWER AFTER THOROUGH ANALYSIS OF THE USER QUERY",
            description="You are the UOB Bank Loan expert specifically appointed to answer the Loan related question",
            llm_config={"config_list": llm_config},
        )

        
        self.customer_assitant = autogen.ConversableAgent(
            name="customer_assitant",
            system_message="You are UOB Bank Customer Assistant. you can help to find any information related to queries on Insurance"
                    "ASSUME USER HAS PERSONAL LOAN IN UOB Bank ALREADY and tailor your recommendation based on that with some best offers"
                    "DO NOT REPLY MULTIPLE TIMES TO THE USER CONSECUTIVELY. RESPOND BACK TO USER IN SINGLE ANSWER AFTER THOROUGH ANALYSIS OF THE USER QUERY"
                    "Ensure to include results from both OCBC and UOB websites only when user asks with the intention of comparison"
                    "DO NOY CROSS SELL: MEANING DO NOT RECOMMEND CREDIT CARD WHEN YOU ARE EMPLOYED TO ANSWER INSURANCE RELATED QUESTION ONLY"
                    "Summarize your answer not more than 50 words",
            description="You are the UOB Bank Loan expert specifically appointed to answer the Insurance related question",
            llm_config={"config_list": llm_config}
        )


        self.loan_assitant.register_for_llm(
            name="bing_search", description="a tool to answer customer question from bing_search function"
            )(bing_search)
        self.executor.register_for_execution(name="bing_search")(bing_search)

        self.information_recommender_agent.register_for_llm(
            name="information_bing_search",
            description="a tool to answer customer question from bing_search function. Ensure to include results from both OCBC and UOB websites."
            )(bing_search)
        self.executor.register_for_execution(name="information_bing_search")(bing_search)


        self.personalised_credit_recommender_agent.register_for_llm(
            name="get_customer_details",
            description="Get the customer details from the customer database"
            )(get_customer_details)
        self.executor.register_for_execution(name="get_customer_details")(get_customer_details)

        self.personalised_credit_recommender_agent.register_for_llm(
            name="personalised_bing_search",
            description="Get the customer details from the customer database"
            )(bing_search)
        self.executor.register_for_execution(name="personalised_bing_search")(bing_search)

        # add the queues to communicate 
        self.user_proxy.set_queues(self.client_sent_queue, self.client_receive_queue)

        # create the group chat
        self.groupchat = autogen.GroupChat(agents=[
            self.user_proxy, 
            self.executor, 
            self.loan_assitant,
            # self.credit_recommender_agent,
            self.customer_assitant,
            self.information_recommender_agent,
            self.personalised_credit_recommender_agent
            ],
        messages=[],
        max_round=25)
        self.manager = CustomGroupChatManager(groupchat=self.groupchat, 
            llm_config={"config_list":llm_config},
            human_input_mode="ALWAYS" ) 

        self.manager.set_queues(self.client_sent_queue, self.client_receive_queue)    

    async def start(self, message):
        await self.user_proxy.a_initiate_chat(
            self.manager,
            clear_history=True,
            message=message
        )