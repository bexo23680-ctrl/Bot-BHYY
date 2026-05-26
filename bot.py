import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import BadRequest, Forbidden
from database import Database
import uuid

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
db = Database()

# معرفات المشرفين (ضع معرف التليجرام الخاص بك هنا)
ADMIN_IDS = [8798182716]  # غير هذا إلى معرفك الحقيقي

# معرف القناة
CHANNEL_USERNAME = "@pngo2"
CHANNEL_ID = "@pngo2"  # يمكن استخدام المعرف الرقمي أيضا

async def check_subscription(user_id, context):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        
        # التحقق من حالة العضوية
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except (BadRequest, Forbidden) as e:
        logger.error(f"Error checking subscription: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

async def subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة الاشتراك الإجباري"""
    keyboard = [
        [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ *يجب الاشتراك في القناة أولاً*\n\n"
        f"عليك الاشتراك في قناة {CHANNEL_USERNAME} لتتمكن من استخدام البوت.\n\n"
        f"بعد الاشتراك، اضغط على زر 'تحقق من الاشتراك'",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def is_admin(user_id):
    """التحقق مما إذا كان المستخدم مشرفاً"""
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الاشتراك أولاً
    is_subscribed = await check_subscription(user_id, context)
    
    if not is_subscribed and not await is_admin(user_id):
        await subscription_required(update, context)
        return
    
    # إنشاء أو الحصول على المستخدم
    anonymous_id = db.get_or_create_user(user_id, user.username)
    
    # تنظيف البيانات المؤقتة
    context.user_data.clear()
    
    welcome_message = f"""
🎭 *مرحباً بك في بوت المراسلة المجهولة!*

🔒 المعرف المجهول الخاص بك: `{anonymous_id}`

📝 *اختر من القائمة:*
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 إرسال رسالة مجهولة", callback_data="send_anonymous")],
        [InlineKeyboardButton("📨 استقبال الرسائل", callback_data="receive_messages")],
        [InlineKeyboardButton("📢 إرسال للقناة", callback_data="send_to_channel")],
        [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
        [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("🚫 حظر/تفعيل الاستقبال", callback_data="toggle_block")]
    ]
    
    # إضافة أزرار المشرفين
    if await is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 لوحة المشرف", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    user_id = update.effective_user.id
    
    # التحقق من الاشتراك
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed and not await is_admin(user_id):
        await subscription_required(update, context)
        return
    
    help_text = """
📚 *دليل استخدام البوت*

1️⃣ *لإرسال رسالة مجهولة:*
   - اضغط على "📤 إرسال رسالة مجهولة"
   - أدخل المعرف المجهول للشخص
   - اكتب رسالتك وستصل دون الكشف عن هويتك

2️⃣ *لإرسال للقناة:*
   - اضغط على "📢 إرسال للقناة"
   - اكتب رسالتك وستنشر في القناة بشكل مجهول

3️⃣ *لاستقبال الرسائل المجهولة:*
   - اضغط على "📨 استقبال الرسائل"
   - سترى أحدث الرسائل المجهولة التي وصلتك

4️⃣ *مشاركة معرفك:*
   - اضغط على "🔗 الحصول على رابطي" لمشاركته

⚠️ *تنبيه مهم:* 
الرجاء استخدام البوت بمسؤولية وعدم إرسال محتوى مسيء.
"""
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية"""
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ تم إلغاء العملية.",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Button pressed: {callback_data} by user {user_id}")
    
    # التحقق من الاشتراك لجميع الأزرار
    if callback_data != "check_subscription":
        is_subscribed = await check_subscription(user_id, context)
        if not is_subscribed and not await is_admin(user_id):
            await query.edit_message_text(
                f"⚠️ *يجب الاشتراك في القناة أولاً*\n\n"
                f"عليك الاشتراك في قناة {CHANNEL_USERNAME} لتتمكن من استخدام البوت.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
                    [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")]
                ])
            )
            return
    
    try:
        # التحقق من الاشتراك
        if callback_data == "check_subscription":
            is_subscribed = await check_subscription(user_id, context)
            
            if is_subscribed or await is_admin(user_id):
                await query.edit_message_text(
                    "✅ *تم التحقق من اشتراكك بنجاح!*\n\nيمكنك الآن استخدام البوت.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎭 ابدأ الاستخدام", callback_data="back_to_menu")]
                    ])
                )
            else:
                await query.answer("❌ لم تشترك في القناة بعد!", show_alert=True)
        
        # العودة للقائمة الرئيسية
        elif callback_data == "back_to_menu":
            context.user_data.clear()
            
            keyboard = [
                [InlineKeyboardButton("📤 إرسال رسالة مجهولة", callback_data="send_anonymous")],
                [InlineKeyboardButton("📨 استقبال الرسائل", callback_data="receive_messages")],
                [InlineKeyboardButton("📢 إرسال للقناة", callback_data="send_to_channel")],
                [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
                [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")],
                [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
                [InlineKeyboardButton("🚫 حظر/تفعيل الاستقبال", callback_data="toggle_block")]
            ]
            
            if await is_admin(user_id):
                keyboard.append([InlineKeyboardButton("👑 لوحة المشرف", callback_data="admin_panel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎭 *القائمة الرئيسية*\nاختر ما تريد القيام به:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # إرسال رسالة للقناة
        elif callback_data == "send_to_channel":
            context.user_data['state'] = 'sending_to_channel'
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📢 *إرسال رسالة مجهولة للقناة*\n\n"
                f"اكتب رسالتك الآن وسيتم نشرها في قناة {CHANNEL_USERNAME} بشكل مجهول.\n\n"
                f"⚠️ *تنبيه:* الرسائل المسيئة سيتم حذفها وقد تتعرض للحظر.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # إرسال رسالة مجهولة
        elif callback_data == "send_anonymous":
            context.user_data['state'] = 'searching'
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔍 *البحث عن مستخدم*\n\n"
                "أدخل المعرف المجهول للشخص الذي تريد مراسلته:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # استقبال الرسائل
        elif callback_data == "receive_messages":
            recent_messages = db.get_received_messages(user_id, limit=10)
            
            if not recent_messages:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📭 *لا توجد رسائل بعد*\n\n"
                    "شارك معرفك المجهول أو رابطك مع أصدقائك لاستقبال رسائل مجهولة!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                messages_text = "📨 *أحدث رسائلك المجهولة:*\n\n"
                
                for i, msg in enumerate(recent_messages, 1):
                    preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    messages_text += f"*{i}.* {preview}\n"
                    messages_text += f"   📅 _{msg['date']}_\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("📋 عرض بتفصيل", callback_data="view_full_messages")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                context.user_data['messages'] = recent_messages
                context.user_data['message_index'] = 0
                
                await query.edit_message_text(
                    messages_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # عرض الرسائل الكاملة
        elif callback_data == "view_full_messages":
            messages = context.user_data.get('messages', [])
            current_index = context.user_data.get('message_index', 0)
            
            if not messages:
                await query.edit_message_text(
                    "❌ لا توجد رسائل للعرض.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
                    ]])
                )
                return
            
            if 0 <= current_index < len(messages):
                msg = messages[current_index]
                message_text = f"""
📨 *رسالة مجهولة* ({current_index + 1}/{len(messages)})

📝 *المحتوى:*
{msg['content']}

📅 *التاريخ:* {msg['date']}
"""
                keyboard = []
                
                nav_buttons = []
                if current_index > 0:
                    nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev_message"))
                if current_index < len(messages) - 1:
                    nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="next_message"))
                
                if nav_buttons:
                    keyboard.append(nav_buttons)
                
                keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # التنقل بين الرسائل
        elif callback_data == "next_message":
            if 'message_index' in context.user_data:
                context.user_data['message_index'] += 1
            await button_callback(update, context)
        
        elif callback_data == "prev_message":
            if 'message_index' in context.user_data:
                context.user_data['message_index'] -= 1
            await button_callback(update, context)
        
        # الحصول على الرابط
        elif callback_data == "get_link":
            anonymous_id = db.get_anonymous_id(user_id)
            
            if anonymous_id:
                bot_username = context.bot.username
                link = f"https://t.me/{bot_username}?start={anonymous_id}"
                
                keyboard = [
                    [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔗 *رابطك المجهول:*\n`{link}`\n\n"
                    f"أو استخدم معرفك: `{anonymous_id}` للبحث المباشر",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # معرفي المجهول
        elif callback_data == "my_id":
            anonymous_id = db.get_anonymous_id(user_id)
            
            if anonymous_id:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`\n\n"
                    f"شارك هذا المعرف مع أصدقائك ليتمكنوا من مراسلتك!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # الإحصائيات
        elif callback_data == "stats":
            user_stats = db.get_user_stats(user_id)
            
            if user_stats:
                sent_count = user_stats['sent']
                received_count = user_stats['received']
                is_blocked = user_stats['blocked']
                
                stats_text = f"""
📊 *إحصائياتك:*

✉️ الرسائل المرسلة: {sent_count}
📨 الرسائل المستلمة: {received_count}
🚫 حالة استقبال الرسائل: {'موقوف ❌' if is_blocked else 'مفعل ✅'}
"""
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    stats_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # تبديل الحظر
        elif callback_data == "toggle_block":
            current_status = db.toggle_block(user_id)
            status_text = "تم إيقاف استقبال الرسائل المجهولة 🚫" if current_status else "تم تفعيل استقبال الرسائل المجهولة ✅"
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(status_text, reply_markup=reply_markup)
        
        # لوحة المشرف
        elif callback_data == "admin_panel":
            if not await is_admin(user_id):
                await query.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)
                return
            
            admin_text = """
👑 *لوحة تحكم المشرف*

📊 *إحصائيات عامة:*
- عدد المستخدمين: جاري التحميل...
- عدد الرسائل: جاري التحميل...

🛠 *الأوامر المتاحة:*
- `/ban [user_id]` - حظر مستخدم
- `/unban [user_id]` - فك حظر مستخدم
- `/broadcast [message]` - إرسال رسالة للجميع
- `/stats_all` - إحصائيات كاملة
"""
            keyboard = [
                [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="banned_list")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                admin_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # قائمة المحظورين
        elif callback_data == "banned_list":
            if not await is_admin(user_id):
                await query.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)
                return
            
            banned_users = db.get_banned_users()
            
            if not banned_users:
                banned_text = "📋 *لا يوجد مستخدمين محظورين*"
            else:
                banned_text = "📋 *قائمة المحظورين:*\n\n"
                for user in banned_users:
                    banned_text += f"- `{user['user_id']}` ({user['username'] or 'بدون اسم'})\n"
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة المشرف", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                banned_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # إلغاء الإرسال
        elif callback_data == "cancel_send":
            context.user_data.clear()
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ تم إلغاء العملية.",
                reply_markup=reply_markup
            )
        
        # إرسال رسالة أخرى لنفس المستلم
        elif callback_data.startswith("send_again_"):
            anonymous_id = callback_data.replace("send_again_", "")
            context.user_data['recipient_id'] = anonymous_id
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✉️ اكتب رسالتك الجديدة الآن.",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ. الرجاء المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
            ]])
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الرسائل النصية"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # التحقق من الاشتراك
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed and not await is_admin(user_id):
        await subscription_required(update, context)
        return
    
    # التحقق من الحظر
    if db.is_user_banned(user_id):
        await update.message.reply_text(
            "🚫 *أنت محظور من استخدام البوت*\n\n"
            "تم حظرك من قبل المشرفين.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    state = context.user_data.get('state')
    
    # إرسال للقناة
    if state == 'sending_to_channel':
        try:
            # إرسال الرسالة للقناة
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_text}\n\n💡 *تم الإرسال عبر بوت المراسلة المجهولة*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تسجيل الرسالة
            db.record_channel_message(user_id, message_text)
            
            keyboard = [
                [InlineKeyboardButton("📢 إرسال رسالة أخرى", callback_data="send_to_channel")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ *تم إرسال رسالتك المجهولة إلى القناة بنجاح!*\n\n"
                f"ستظهر رسالتك في قناة {CHANNEL_USERNAME}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending to channel: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ أثناء إرسال الرسالة للقناة."
            )
        
        context.user_data.clear()
        return
    
    # البحث عن مستخدم
    if state == 'searching':
        user_info = db.get_user_by_anonymous_id(message_text)
        
        if user_info:
            if user_info['is_blocked']:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🚫 هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً.",
                    reply_markup=reply_markup
                )
            else:
                context.user_data['recipient_id'] = message_text
                context.user_data['state'] = 'sending'
                
                keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ تم العثور على المستخدم!\n\n"
                    f"✉️ *اكتب رسالتك الآن وسيتم إرسالها مباشرة.*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        else:
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ لم يتم العثور على مستخدم بهذا المعرف.\n"
                "تأكد من المعرف وحاول مرة أخرى.",
                reply_markup=reply_markup
            )
        
        return
    
    # إرسال رسالة لمستخدم
    if 'recipient_id' in context.user_data:
        recipient_anonymous_id = context.user_data['recipient_id']
        recipient_info = db.get_user_by_anonymous_id(recipient_anonymous_id)
        
        if recipient_info:
            recipient_real_id = recipient_info['user_id']
            
            if db.is_blocked(recipient_real_id):
                await update.message.reply_text(
                    "❌ هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً."
                )
            else:
                try:
                    await context.bot.send_message(
                        chat_id=recipient_real_id,
                        text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_text}\n\n💡 للرد أو الاطلاع على رسائلك، استخدم /start",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    db.record_message(user_id, recipient_real_id, message_text)
                    
                    keyboard = [
                        [InlineKeyboardButton("📤 إرسال رسالة أخرى", callback_data=f"send_again_{recipient_anonymous_id}")],
                        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "✅ *تم إرسال رسالتك المجهولة بنجاح!*",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    await update.message.reply_text(
                        "❌ حدث خطأ أثناء إرسال الرسالة."
                    )
        else:
            await update.message.reply_text(
                "❌ رابط غير صالح أو منتهي الصلاحية."
            )
        
        context.user_data.clear()
        return
    
    # رسالة افتراضية
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 أهلاً! استخدم القائمة للتنقل أو أرسل /start.",
        reply_markup=reply_markup
    )

# أوامر المشرفين
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر حظر مستخدم - للمشرفين فقط"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ استخدم الأمر كالتالي: `/ban [user_id]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون سبب"
        
        db.ban_user(target_id, reason)
        
        await update.message.reply_text(
            f"✅ تم حظر المستخدم `{target_id}`\n"
            f"السبب: {reason}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # محاولة إعلام المستخدم المحظور
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🚫 *تم حظرك من استخدام البوت*\n\n"
                f"السبب: {reason}\n\n"
                f"للتواصل مع المشرفين: @pngo2",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً!")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فك حظر مستخدم - للمشرفين فقط"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ استخدم الأمر كالتالي: `/unban [user_id]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        target_id = int(context.args[0])
        
        db.unban_user(target_id)
        
        await update.message.reply_text(
            f"✅ تم فك حظر المستخدم `{target_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # محاولة إعلام المستخدم
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ *تم فك حظرك من البوت*\n\nيمكنك الآن استخدام البوت مرة أخرى.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text("❌ معرف المستخدم يجب أن يكون رقماً!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر إرسال رسالة للجميع - للمشرفين فقط"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ استخدم الأمر كالتالي: `/broadcast [الرسالة]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    message = " ".join(context.args)
    users = db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"📤 جاري إرسال الرسالة إلى {len(users)} مستخدم...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *رسالة من المشرفين:*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent_count += 1
        except:
            failed_count += 1
    
    await update.message.reply_text(
        f"✅ *تم إرسال الرسالة*\n\n"
        f"✓ تم الإرسال: {sent_count}\n"
        f"✗ فشل الإرسال: {failed_count}",
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات كاملة - للمشرفين فقط"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    stats = db.get_global_stats()
    
    stats_text = f"""
📊 *إحصائيات البوت العامة*

👥 *المستخدمين:*
- إجمالي المستخدمين: {stats['total_users']}
- المستخدمين النشطين: {stats['active_users']}
- المحظورين: {stats['banned_users']}

📨 *الرسائل:*
- إجمالي الرسائل: {stats['total_messages']}
- رسائل القناة: {stats['channel_messages']}

📅 *آخر تحديث:* {stats['last_update']}
"""
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

def main():
    """تشغيل البوت"""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("لم يتم العثور على TELEGRAM_BOT_TOKEN!")
        return
    
    logger.info("جاري تشغيل البوت...")
    
    application = Application.builder().token(TOKEN).build()
    
    # الأوامر الأساسية
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # أوامر المشرفين
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats_all", stats_all))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # معالج الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("البوت جاهز للعمل!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
