import schedule
from threading import Thread
import logging
import gspread
import os
import pytz
import telegram
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ChatAction
from telegram import user
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext)
from functools import wraps
from time import sleep

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Set scope to use when authenticating:
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/drive']

path = '/app'

creds = ServiceAccountCredentials.from_json_keyfile_name(path + '/creds.json', scope)

client = gspread.authorize(creds)
sheet = client.open('Seletar SFT Records').worksheet('ARMCEG')
PORT = int(os.environ.get('PORT', '8443'))


my_date = datetime.now(pytz.timezone('Asia/Singapore')).strftime('%d/%m/%Y')

#FlowChart: SIGN_IN --> CHECKHEALTH --> NAME --> ACTIVITY --> CONFIRMATION --> SUBMIT --> SIGNOUT
#FlowChart: SIGN_IN --> CHECKHEALTH --> NAME --> ACTIVITY --> ROUTECONFIRMATION --> CONFIRMATION --> SUBMIT --> SIGNOUT

SIGN_IN, CHECKHEALTH, NAME, ACTIVITY, ROUTECONFIRMATION, CONFIRMATION, LOCATIONCONF, SUBMIT, SIGNOUT = range(9)

def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)

def function_to_run():
    for userID in userID_database:
        bot.send_message(userID, "This is a friendly reminder to sign out of SFT Bot!")
    return

# Show that bot it "TYPING"
def send_typing_action(func):
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

#Dictionary that maps a number to activity
activity_dict = {'1': "Run", '2': "Gym", '3': "Sports and Games", '4':'Statics'}
route_dict = {'1': "Stadium", '2': "1km", '3': "2km", '4': "3.2km", '5': "MEC"}
location_dict = {'1': "Stadium", '2': "Parade Square", '3': "Buaya Square", '4': "Training Sheds", '5': "MEC"}

# the database in a form of dictionary. The user's ID is used as the key, and value is a list
# of data collected by asking the questions. Each key will have a list of its own, and when the
# user signs out or cancels the conversation, the key-value pair will be deleted.
#User ID is used as the key, and index refers to the specific row that the User's ID is written. Used to edit data when signing out.
userID_savedindex = {}
userID_database = {}

@send_typing_action
def password(update: Update, _: CallbackContext):
    # Ask for password
        morning_start =  '07:00'
        night_end = '22:00'
        now = datetime.now(pytz.timezone('UTC'))
        singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
        check_in_time = singapore_time.strftime("%H:%M")
        if (check_in_time >= morning_start and check_in_time <= night_end):
            userID = str(update.message.chat_id)
            if userID not in userID_database:
                userID_database[userID] = []
                update.message.reply_text(
                'Hi! My name is Armceg Bot.\n'
                'I will help you sign in for Self-Organized Fitness Training. \n\n'
                'Please enter the password.\n\n'
                'Send /cancel to stop talking to me.', reply_markup=ReplyKeyboardRemove()
                )
                return CHECKHEALTH

            else:
                    update.message.reply_text(
                        'Please sign out from your previous session before starting a new session.'
                    )
                    ConversationHandler.END

        else:
            update.message.reply_text(
            'The time now is: ' + str(check_in_time) + '\n\n'
            'It is currently not within SFT Timings. Sign In cancelled. \n\n'
            'SFT Timings are: <b>0700hrs - 2200hrs</b>.', parse_mode='HTML'
            )
            return ConversationHandler.END

@send_typing_action
def check_health(update: Update, _: CallbackContext):
    # A list of questions for the User to read through before continuing with the form. Sent as a photo.
    # If he says Yes to any of the questions listed, End conversation.
    if update.message.text == 'ARMCEG':
        reply_keyboard = [['Yes', 'No']]
        filename = "/app/Checklist.png"
        update.message.bot.send_photo(update.message.chat_id,open(filename,'rb'),caption=
        'Pre-Activity Checklist from SFT Training Directive')
        update.message.reply_text(
        '<b>GET ACTIVE QUESTIONNAIRE</b>\n\n'
        'If any of the above is yes, select \'Yes\'.\n'
        'Otherwise, select \'No\'.', parse_mode='HTML', reply_markup = ReplyKeyboardMarkup(reply_keyboard))
    
        return NAME

    elif update.message.text == '/cancel':
        userID = str(update.message.chat_id)
        userID_database.pop(userID,None)
        update.message.reply_text(
        'Sign In cancelled, Have a nice day!')
        return ConversationHandler.END
    # Ends conversation when password is wrong
    else:
        update.message.reply_text(
        'Wrong password, please reattempt the sign in by /start '
        )
        userID = str(update.message.chat_id)
        userID_database.pop(userID,None)
        return ConversationHandler.END

@send_typing_action
def name(update: Update, _: CallbackContext):
     # If user says No to all questions on PARQ, Continues Sign in Process, asks for name of Person 
    if update.message.text == 'No' or update.message.text == 'no':
        update.message.reply_text(
        'Please put your full name.', reply_markup=ReplyKeyboardRemove() )
        return ACTIVITY

    # If user says Yes to any questions, Quits Sign in Process
    elif update.message.text == 'Yes' or update.message.text == 'yes':
        update.message.reply_text(
        'Please consult your Unit Medical Officer before you commence training.\n\n' 
        'Sign In cancelled.', reply_markup=ReplyKeyboardRemove()
        )
        userID = str(update.message.chat_id)
        userID_database.pop(userID,None)
        return ConversationHandler.END
    else:
        #Non applicable answers
        update.message.reply_text(
        'Please answer Yes or No.', reply_markup=ReplyKeyboardRemove()
        )

@send_typing_action
def activity(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
    userID_database[userID].append(str(my_date))
    userID_database[userID].append(update.message.text)
    reply_keyboard = [['1','2','3','4']]
    update.message.reply_text(
            'What activity would you be doing today?\n'
            'Please choose an option. \n\n'
            '1: Run 🏃 \n'
            '2: Gym \N{flexed biceps} \n'
            '3: Sports and Games ⛹️ \n'
            '4: Statics \n'
            'Send /cancel to stop talking to me.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard),
        )
    return ROUTECONFIRMATION        

@send_typing_action
def route_confirmation(update: Update, _: CallbackContext):
    if update.message.text == '1':
        userID = str(update.message.chat_id)
        userID_database[userID].append(activity_dict[update.message.text])
        reply_keyboard = [['1','2','3','4','5']]
        update.message.reply_text(
            'Which route will you be running today? \n'
            'Please choose an option \n\n'
            '1: Stadium \n'
            '2: 1km \n'
            '3: 2km \n'
            '4: 3.2km \n'
            '5: MEC \n'
            'Send /cancel to stop talking to me.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard),
        )
        return CONFIRMATION

    elif update.message.text == '4':
        userID = str(update.message.chat_id)
        userID_database[userID].append(activity_dict[update.message.text])
        reply_keyboard = [['1','2','3','4','5']]
        update.message.reply_text(
            'Where will you be doing your statics at?'
            'Please choose an option \n\n'
            '1: Stadium \n'
            '2: Parade Square \n'
            '3: Buaya Square \n'
            '4: Training Sheds \n'
            '5: MEC \n'                       
            'Send /cancel to stop talking to me.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard),
        )
        return LOCATIONCONF

    elif update.message.text == '2':
        userID = str(update.message.chat_id)
        userID_database[userID].append(activity_dict[update.message.text])
        userID_database[userID].append('Gym')
        now = datetime.now(pytz.timezone('UTC'))
        singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
        time_start = singapore_time.strftime("%H:%M")
        userID_database[userID].append(time_start)
        update.message.reply_text('Please check your details before submitting.\n')
        update.message.reply_text(
                'Date: ' + userID_database[userID][0] + '\n \n'
                'Name: ' + userID_database[userID][1] + '\n \n'
                'Activity: ' + str(userID_database[userID][2]) + '\n \n'
                'Location/Route: ' + (userID_database[userID][3]) + '\n \n'
                'Sign In Time: ' + userID_database[userID][4]) 

        reply_keyboard = [['Yes', 'No']]
        update.message.reply_text('Are they correct? \n \n'
                            'Enter Yes or No.',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard = True))
        return SUBMIT
        
    else:
        userID = str(update.message.chat_id)
        userID_database[userID].append(activity_dict[update.message.text])
        userID_database[userID].append('Bball/Soccer Court')
        now = datetime.now(pytz.timezone('UTC'))
        singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
        time_start = singapore_time.strftime("%H:%M")
        userID_database[userID].append(time_start)
        update.message.reply_text('Please check your details before submitting.\n')
        update.message.reply_text(
                'Date: ' + userID_database[userID][0] + '\n \n'
                'Name: ' + userID_database[userID][1] + '\n \n'
                'Activity: ' + str(userID_database[userID][2]) + '\n \n'
                'Location/Route: ' + (userID_database[userID][3]) + '\n \n'
                'Sign In Time: ' + userID_database[userID][4]) 

        reply_keyboard = [['Yes', 'No']]
        update.message.reply_text('Are they correct? \n \n'
                            'Enter Yes or No.',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard = True))
        return SUBMIT

@send_typing_action
def confirmation(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
        #shows the user all of the data that was submitted, to check before submitting
    userID = str(update.message.chat_id)
    userID_database[userID].append(route_dict[update.message.text]) 
    now = datetime.now(pytz.timezone('UTC'))
    singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
    time_start = singapore_time.strftime("%H:%M")
    userID_database[userID].append(time_start)
    update.message.reply_text('Please check your details before submitting.\n')
    update.message.reply_text(
                'Date: ' + userID_database[userID][0] + '\n \n'
                'Name: ' + userID_database[userID][1] + '\n \n'
                'Activity: ' + str(userID_database[userID][2]) + '\n \n'
                'Location/Route: ' + (userID_database[userID][3]) + '\n \n'
                'Sign In Time: ' + userID_database[userID][4])

    reply_keyboard = [['Yes', 'No']]
    update.message.reply_text('Are they correct? \n \n'
                            'Enter Yes or No.',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard = True))
            
    return SUBMIT

@send_typing_action
def location(update: Update, _: CallbackContext):
    userID = str(update.message.chat_id)
        #shows the user all of the data that was submitted, to check before submitting
    userID = str(update.message.chat_id)
    userID_database[userID].append(location_dict[update.message.text]) 
    now = datetime.now(pytz.timezone('UTC'))
    singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
    time_start = singapore_time.strftime("%H:%M")
    userID_database[userID].append(time_start)
    update.message.reply_text('Please check your details before submitting.\n')
    update.message.reply_text(
                'Date: ' + userID_database[userID][0] + '\n \n'
                'Name: ' + userID_database[userID][1] + '\n \n'
                'Activity: ' + str(userID_database[userID][2]) + '\n \n'
                'Location/Route: ' + (userID_database[userID][3]) + '\n \n'
                'Sign In Time: ' + userID_database[userID][4])

    reply_keyboard = [['Yes', 'No']]
    update.message.reply_text('Are they correct? \n \n'
                            'Enter Yes or No.',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard = True))
            
    return SUBMIT

@send_typing_action
def submit(update: Update, _: CallbackContext):
    #if data is correct --> Yes, then data will be uploaded onto excel
    if update.message.text == 'Yes' or update.message.text == 'yes':
        print(userID_database)
        userID = str(update.message.chat_id)
        # Program to add to GOOGLE SHEETS HERE!
        Date = userID_database[userID][0]
        Person = userID_database[userID][1]
        Activity = userID_database[userID][2]
        LocationRoute = userID_database [userID][3]
        Time_start = userID_database[userID][4]
        client = gspread.authorize(creds)
        sheet = client.open('Seletar SFT Records').worksheet('ARMCEG')
        data = sheet.get_all_records()
        row_to_insert = [Date,Person, Activity, LocationRoute, Time_start]
        userID_savedindex[userID] = len(data) +2
        sheet.insert_row(row_to_insert, len(data) + 2)
        #inform user that sign in has been completed
        update.message.reply_text(
            '<b>Sign in completed!</b> \n\n'
            'Some Safety Pointers to note: \n\n'
            '1) All participants must remain contactable during their SFT. \n\n'
            '2) Please be reminded that you are supposed to: \n\n'
            '   - Wear proper PT kit, \n\n'
            '   - Perform PT that you are medically allowed,\n\n'
            '   - Perform activity only at permitted location,\n\n'
            '   - Ensure that the weather is clear,\n\n'
            '   - Ensure to look after your own safety.\n\n'
            '3) No high risk/dangerous activity is allowed during SFT. When in doubt, seek permission from PSOs before execution. \n\n'
            'Stay Safe & have a great workout! \n\n'
            '<b>Enter /end to sign out from SFT</b>', parse_mode= 'HTML', reply_markup=ReplyKeyboardRemove()
        )
        #Sends sign in notification to respective subunit channels
        bot.sendMessage(chat_id = -1001599199449, text = (
                                                        '🏃New Sign In Entry🏃' + '\n\n'
                                                        'Date: ' + Date + '\n'
                                                        'Name: ' + Person + '\n'
                                                        'Activity: ' + Activity + '\n'
                                                        'Location/Route: ' + LocationRoute + '\n'
                                                        'Sign in Time: ' + Time_start
                                                        ) )

        return ConversationHandler.END

    else: 
        #if no, ends conversation. 
        update.message.reply_text(
        'Sign In cancelled, Have a nice day!')
        userID = str(update.message.chat_id)
        userID_database.pop(userID,None)
        return ConversationHandler.END

@send_typing_action
def check_end(update: Update, _: CallbackContext):
    #if User's ID (key) not inside the dictionary, means no sign in data. 
    userID = str(update.message.chat_id)
    if userID not in userID_database:
        update.message.reply_text(
            'There is no sign in data. You have already signed out. ')
        return ConversationHandler.END

    else:
        reply_keyboard = [['Yes', 'No']]
        # Checks with user if he really wants to sign out
        now = datetime.now(pytz.timezone('UTC'))
        singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
        time_end = singapore_time.strftime("%H:%M")
        update.message.reply_text(
            'The time now is: ' + str(time_end) + '\n'
            'Are you sure you want to sign out? \n'
            'Tap Yes to continue \n', reply_markup=ReplyKeyboardMarkup(reply_keyboard)
        )
        return SIGNOUT

@send_typing_action
def sign_out(update: Update, _: CallbackContext):
    if update.message.text == 'Yes' or update.message.text == 'yes':
        # PROGRAM TO ADD SIGN OUT TIME TO GOOGLE SHEETS GO HERE
        userID = str(update.message.chat_id)
        now = datetime.now(pytz.timezone('UTC'))
        singapore_time = now.astimezone(pytz.timezone('Asia/Singapore'))
        Time_end = singapore_time.strftime("%H:%M")
        # userID_database[userID].append(time_end)
        sheet.delete_rows(userID_savedindex[userID])
        Date = userID_database[userID][0]
        Person = userID_database[userID][1]
        Activity = userID_database[userID][2]
        LocationRoute = userID_database[userID][3]
        Time_start = userID_database[userID][4]
        row_to_insert = [Date,Person, Activity, LocationRoute, Time_start,Time_end]
        sheet.insert_row(row_to_insert, userID_savedindex[userID])
        update.message.reply_text(
            'Sign out completed, have a nice day!\n',reply_markup=ReplyKeyboardRemove()
        )
        #sends sign out notification to respective subunit channels
        bot.sendMessage(chat_id = -1001599199449, text = (
                                                        '😴New Sign Out Entry😴'  + '\n\n'
                                                        'Date: ' + Date + '\n'
                                                        'Name: ' + Person + '\n'
                                                        'Activity: ' + Activity + '\n'
                                                        'Location/Route: '+ LocationRoute + '\n'
                                                        'Sign Out Time: ' + Time_end
                                                        ) )
        
        userID = str(update.message.chat_id)
        userID_database.pop(userID,None)
        print(userID_database)
        return ConversationHandler.END
    else:
        #if no, ends conversation. Pending sign out
        update.message.reply_text(
        'Sign Out cancelled, Have a nice day!')
        return ConversationHandler.END

@send_typing_action
def correct_format(update: Update, _: CallbackContext):
    #for any errors in submission, Bot will send this to user.
    update.message.delete()
    update.message.reply_text(
        'It seems like there was an error. \n'
        'Please type it in the appropriate format: \n\n'
        'For Name: Name \n\n'
        'For Activity: 1/2/3/4 (Choose one) \n\n '
        'For Location/Route: 1/2/3/4/5 (Choose one) \n\n'
        'Please input the correct format', reply_markup=ReplyKeyboardRemove() )

@send_typing_action
def cancel(update: Update, _: CallbackContext):
    #if user sends /cancel command, ends conversation
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Sign in cancelled, have a great day!', reply_markup=ReplyKeyboardRemove()
    )
    userID = str(update.message.chat_id)
    userID_database.pop(userID,None)
    return ConversationHandler.END

@send_typing_action
def delete_msg(update: Update, _: CallbackContext):
    #Bot will delete any unnecessary messages
    update.message.delete()
    update.message.reply_text(
        'Please don\'t send me unnecessary things like GIFs and Stickers, Thank you.')

@send_typing_action
def yesno(update: Update, _: CallbackContext):
    update.message.reply_text(
        'Please input Yes or No. Thank you')
    
def main() -> None:
    #Run Bot
    # Create the Updater and pass it your bot's token.
    print(userID_database)
    TOKEN = os.environ["TOKEN"]
    global bot
    bot = telegram.Bot(token=TOKEN)
    updater = Updater(TOKEN)


    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start',password)],
        states = {
            CHECKHEALTH: [MessageHandler(Filters.text, check_health)],
            NAME: [MessageHandler(Filters.text, name)],
            ACTIVITY: [MessageHandler(Filters.text,activity)],
            ROUTECONFIRMATION: [MessageHandler(Filters.regex('^[1-5]$'), route_confirmation)],
            LOCATIONCONF: [MessageHandler(Filters.regex('^[1-5]$'), location)],
            CONFIRMATION: [MessageHandler(Filters.regex('^[1-5]$'), confirmation)],
            SUBMIT: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), submit)],
                },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.text, correct_format)]
        )


    end_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('end',check_end)],
        states = {SIGNOUT: [MessageHandler(Filters.regex('(?i)^(yes|no)$'), sign_out)]},
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.text, yesno)]
    )

    dispatcher.add_handler(MessageHandler(Filters.sticker|Filters.animation|Filters.audio|Filters.document,delete_msg))
    dispatcher.add_handler(start_conv_handler)
    dispatcher.add_handler(end_conv_handler)
    dispatcher.add_handler(CommandHandler('cancel', cancel))


    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN,webhook_url= 'https://vast-gray-harp-seal-belt.cyclic.app/' + TOKEN)


    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    schedule.every().day.at("02:00").do(function_to_run)
    schedule.every().day.at("13:30").do(function_to_run)
    schedule.every().day.at("13:45").do(function_to_run)
    Thread(target = schedule_checker).start()
    main()
