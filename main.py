import os
import telebot
import telegram
import requests
from keep_alive import keep_alive

keep_alive()
# Create a Telegram Bot object
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telegram.Bot(token=TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
  bot.reply_to(
    message,
    "Hello! Make sure to put the text as: \n\n/getopp <field> in <country name>"
  )

# Handle the "/getopportunity" command
@bot.message_handler(commands=['getopp'])
def handle_get_opportunity(message):
  parts = message.text.split(" in ")
  query = parts[0].split(" ")[1:]

  if len(parts) == 2:
    committee_name = parts[1]
    url = f"https://gis-api.aiesec.org/v2/committees/autocomplete?access_token=797149ff3e2ee6a8abc4f101a77c714caf9463dcb69be8bd5d53e0698064aa91&q={committee_name}&tag=MC"
    response = requests.get(url)
    data = response.json()

    if len(data) == 1:
      committee_id = data[0]["id"]
    else:
      bot.send_message(
        message.chat.id,
        f"Could not find committee with name '{committee_name}'")
      return
  else:
    committee_id = None

  query = " ".join(query)

  # Build the request URL using the provided API endpoint and access token
  url = "https://gis-api.aiesec.org/v2/opportunities?access_token={ACCESS_TOKEN}&api_key={API_KEY}"
  params = {
    "access_token":
    "797149ff3e2ee6a8abc4f101a77c714caf9463dcb69be8bd5d53e0698064aa91",
    "api_key":
    "797149ff3e2ee6a8abc4f101a77c714caf9463dcb69be8bd5d53e0698064aa91",
    "q": query
  }

  if committee_id is not None:
    params["filters[committee]"] = committee_id

  response = requests.get(url, params=params)

  # Extract the opportunities data from the response
  opportunities = response.json()["data"]

  # Build the message to send back to the user
  message_text = "Here are the available opportunities for {}: \n\n".format(
    query)
  bot.send_chat_action(message.chat.id, 'typing')
  for opportunity in opportunities:
    message_text += "Title: {}\n".format(opportunity["title"])
    message_text += "Link: {}\n".format(
      f"https://aiesec.org/opportunity/{opportunity['id']}")
    message_text += "Location: {}\n".format(opportunity["location"])
    message_text += "Product: {}\n".format(
      opportunity["programmes"]["short_name"])

    # URL to get opportunity details
    opportunity_id = opportunity['id']
    opportunity_url = f"https://gis-api.aiesec.org/v2/opportunities/{opportunity_id}?access_token=797149ff3e2ee6a8abc4f101a77c714caf9463dcb69be8bd5d53e0698064aa91"
    opportunity_response = requests.get(opportunity_url)

    # Extract salary data from the response
    opportunity_data = opportunity_response.json()
    specifics_info = opportunity_data.get("specifics_info", {})
    salary_data = specifics_info.get("salary", {})
    salary_currency = specifics_info.get("salary_currency", {})
    salary_alpha = salary_currency.get("alphabetic_code", {})

    message_text += "Salary: {} {}\n".format(salary_data, salary_alpha)

    headers = {
      'Authorization':
      '797149ff3e2ee6a8abc4f101a77c714caf9463dcb69be8bd5d53e0698064aa91'
    }
    queryv2 = '''
            query {{
                getOpportunity(id: "{opportunity_id}") {{
                  available_slots {{
                    start_date
                    end_date
                  }}
                  opportunity_cost
                }}
              }}
            '''.format(opportunity_id=opportunity_id)

    response = requests.post('https://api.aiesec.org/graphql',
                             json={'query': queryv2},
                             headers=headers)
    if response.status_code == 200:
      # Parse the JSON response
      json_data = response.json()

      # Access the list of duration_type objects
      opportunity_cost = json_data['data']['getOpportunity'][
        'opportunity_cost']
      programme_fee = opportunity_cost['programme_fee']
      currency_name = opportunity_cost['currency']
      message_text += "Programme fee: {} {}\n".format(programme_fee,
                                                      currency_name)

      available_slots = json_data['data']['getOpportunity']['available_slots']

      for index, slot in enumerate(available_slots):
        start_date_value = slot['start_date']
        end_date_value = slot['end_date']

        message_text += "Duration: {} - {}".format(start_date_value,
                                                   end_date_value)
        if index < len(available_slots) - 1:
          message_text += "\n"
        else:
          message_text += "\n\n"

  bot.send_message(message.chat.id, message_text)
  
bot.polling()
