# Project Name
## Table of Contents
- [Overview](#Overview)
- [Prerequisites](#prerequisites)
- [Running Locally](#running-locally)
- [Azure based deployment](#azure-based-deployment)

## Overview
![](images/use%20case.jpg)
![](images/agents%20definition.jpg)


## Prerequisites
***Step 1:***

Update the .env file with API Key and Model Endpoint of Azure OpenAI model

Note you can take these details from Azure OpenAI portal or Azure AI Foundry based on the service you use.

`Example model endpoint: https://\<<instancename\>>.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-08-01-preview`

***Step 2:***

### Create a new Conda environment

To create a new python Conda environment named `agentai` with Python 3.11, use the following command:

```sh
conda create --name agentai python=3.11
```

### Activate the conda environment
```sh
conda activate agentai
```

### Install the prerequisite libraries
```sh
pip install -r requirements.txt
```

## Running Locally
To run the backend locally
```sh
uvicorn app:app --host 0.0.0.0 --port 8000
```

Once the application started successfully without error, you can now interact with the backend through postman following the below video

Use the ws://localhost:8000/api/ws/202411121818421162 instead of the ws link in the video. 

`202411121818421162 in the link is the unique websocket id meaning each unique id is the unique websocket connection`


[Video is here, Watch on YouTube](https://www.youtube.com/watch?v=sIiard5HpdY)


`Conversational Flow - Sample Prompts:` 

The below questions are tried in the video as well.

Question 1: My OCBC 365 card is expiring soon. It was a great card with 2% cashback options. Can you suggest similar options with UOB?

Question 2: Ah thanks for the options. But based on my account and recent spend, can you suggest me some UOB cards that might be more suitable to me?

Question 3: I also want to enquire about travel insurance. What are some of the best options available with UOB there?

Question 4: What is the room for me to request for a home loan? This will be on top of my current loan.

## Azure based deployment

Prerequisite: Install Docker Desktop

For deploying on Azure, you need a docker container image hosted on Azure Container Registry, Follow the below steps to build the docker image and host it on Azure Container Registry and then proceed on to create the Azure web app from the hosted Azure Container Registry

***Step 1:***

Build the docker image with below command
```sh
docker build --tag <<image_name>> .
```

***Step 2:***

Run the container locally to see if it running properly
```sh
docker run --detach --publish 8000:8000 <<image_name>>
```

***Step 3:***

Now we can proceed on to host the built container image to ACR and carry on deployment. First, Lets see the Azure Account you have access to running below command in command prompt. First time, You will get the pop up to sign in. So sign in with your credential. second command will give you info about tenant_id required for Step 4

```sh
az account show
az account list --output table
```

***Step 4:***
Get the tenant_id from step 3, and substitue it in the place of tenant_id

```sh
az login --tenant <<tenant_id>>
```

***Step 5:***

Now, we can first create the Azure Container Registry using below comamnd

Substitute the resource group and Azure Container Registry name of your choice in the below command

```sh
az acr create --resource-group <<existing_RG_name>> --name <<acr_name_of_your_choice>> --sku basic --admin-enabled true
```

Now, lets build the container image inside the created the ACR

```sh
az acr build --resource-group <<existing_RG_name>> --registry <<acr_name_of_your_choice>> --image <<image_name_of_your_choice>>:<<version_name>> .
```

Check for the error message in the command prompt. If no error, now proceed on to next Step

***Step 6:***

Its time to create the Azure Web App

For creating the Azure Web App, Azure App Service plan is requires. Lets create that using the below command

```sh
az appservice plan create --name <<serviceplan_name_of_your_choice>> --resource-group <<existing_RG_name>> --sku B1 --is-linux
```

Now that we have created the Service Plan, we can now create the Web App using the created App Service plan details.

```sh
az webapp create -g <<existing_RG_name>> -p <<serviceplan_name_of_your_choice>> -n <<webapp_name_of_your_choice>> -i <<acr_name_of_your_choice>>.azurecr.io/<<image_name_of_your_choice>>:<<version_name>>
```

`Note: In the above command look for the names in the previous steps and substitute it correctly`

***Step 7:***

Azure Web App has been deployed succsessfully. Wait for 15-20 mins and then you can stream logs from Azure Web App by running the below command in the Command prompt. 

```sh
az webapp log tail --resource-group <<existing_RG_name>> --name <<webapp_name_of_your_choice>>
```

After streaming logs, you can now interact with the backend through postman using websocket 

Websocket url will be like this:
```sh
ws://multiagentapp.azurewebsites.net/api/ws/<<wis_d>>
```

Note: Give any random number in place of <<wis_d>> in above command to make a unique websocket connection. 

As soon as you start interacting with backend through postman, you will start receiving the logs in the command prompt. 

Hope you have enjoyed this.