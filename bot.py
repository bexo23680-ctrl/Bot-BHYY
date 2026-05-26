import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from database import Database
import uuid
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
db = Database()

# معرف المشرف الرئيسي
ADMIN_ID = 8798182716
ADMIN_IDS = [ADMIN_ID]

# معرف القناة
CHANNEL_USERNAME = "@pngo2"
CHANNEL_ID = "@pngo2"

async def check_subscription(user_id, context):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        
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
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"⚠️ *يجب الاشتراك في القناة أولاً*\n\n"
            f"عليك الاشتراك في قناة {CHANNEL_USERNAME} لتتمكن من استخدام البوت.\n\n"
            f"بعد الاشتراك، اضغط على زر 'تحقق من الاشتراك'",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
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

async def show_next_pending_message(query, context):
    """عرض الرسالة المعلقة التالية"""
    try:
        pending = db.get_pending_messages()
        
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 العودة للوحة المشرف", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    "📋 *لا توجد رسائل معلقة للمراجعة*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except:
                try:
                    await query.message.reply_text(
                        "📋 *لا توجد رسائل معلقة للمراجعة*",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except:
                    pass
            return
        
        # عرض أول رسالة معلقة
        msg = pending[0]
        message_text = f"""
📋 *رسالة معلقة للمراجعة* (1/{len(pending)})

📝 *المحتوى:*
{msg['content']}

📅 *التاريخ:* {msg['created_at']}
👤 *معرف المرسل:* `{msg['anonymous_id']}`
"""
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول", callback_data=f"approve_{msg['id']}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{msg['id']}")
            ],
            [InlineKeyboardButton("🔙 العودة للوحة المشرف", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تخزين قائمة الرسائل المعلقة
        context.user_data['pending_messages'] = pending
        context.user_data['current_pending_id'] = msg['id']
        
        try:
            await query.edit_message_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except:
            try:
                await query.message.reply_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Error in show_next_pending_message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الاشتراك أولاً
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
        pending_count = len(db.get_pending_messages())
        keyboard.append([InlineKeyboardButton("👑 لوحة المشرف", callback_data="admin_panel")])
        if pending_count > 0:
            keyboard.append([InlineKeyboardButton(f"📋 الرسائل المعلقة ({pending_count})", callback_data="pending_messages")])
    
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
   - اكتب رسالتك
   - سترسل للمشرف للمراجعة ثم تنشر في القناة

3️⃣ *لاستقبال الرسائل المجهولة:*
   - اضغط على "📨 استقبال الرسائل"
   - سترى أحدث الرسائل المجهولة التي وصلتك

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
            await subscription_required(update, context)
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
                pending_count = len(db.get_pending_messages())
                keyboard.append([InlineKeyboardButton("👑 لوحة المشرف", callback_data="admin_panel")])
                if pending_count > 0:
                    keyboard.append([InlineKeyboardButton(f"📋 الرسائل المعلقة ({pending_count})", callback_data="pending_messages")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    "🎭 *القائمة الرئيسية*\nاختر ما تريد القيام به:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except:
                await query.message.reply_text(
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
                f"اكتب رسالتك الآن.\n"
                f"سيتم إرسالها للمشرف للمراجعة ثم تنشر في قناة {CHANNEL_USERNAME}.\n\n"
                f"⚠️ *تنبيه:* الرسائل المسيئة سيتم رفضها.",
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
            
            pending_count = len(db.get_pending_messages())
            banned_count = len(db.get_banned_users())
            
            admin_text = f"""
👑 *لوحة تحكم المشرف*

📊 *معلومات سريعة:*
- الرسائل المعلقة: {pending_count}
- المستخدمين المحظورين: {banned_count}

🛠 *الأوامر المتاحة:*
- `/ban [user_id]` - حظر مستخدم
- `/unban [user_id]` - فك حظر مستخدم
- `/broadcast [message]` - إرسال رسالة للجميع
"""
            keyboard = [
                [InlineKeyboardButton(f"📋 الرسائل المعلقة ({pending_count})", callback_data="pending_messages")],
                [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="banned_list")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                admin_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # الرسائل المعلقة
        elif callback_data == "pending_messages":
            if not await is_admin(user_id):
                await query.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)
                return
            
            await show_next_pending_message(query, context)
        
        # قبول رسالة للقناة
        elif callback_data.startswith("approve_"):
            if not await is_admin(user_id):
                await query.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)
                return
            
            message_id = int(callback_data.replace("approve_", ""))
            
            # التحقق من أن هذه هي الرسالة المعروضة حالياً
            current_pending_id = context.user_data.get('current_pending_id')
            if current_pending_id and current_pending_id != message_id:
                await query.answer("⚠️ هذه ليست الرسالة المعروضة حالياً!", show_alert=True)
                return
            
            # التحقق مما إذا كانت الرسالة لا تزال معلقة
            if not db.is_message_pending(message_id):
                await query.answer("⚠️ هذه الرسالة تمت معالجتها بالفعل!", show_alert=True)
                # تحديث القائمة مباشرة
                await show_next_pending_message(query, context)
                return
            
            # منع المعالجة المتكررة - تعطيل فوري
            db.lock_message(message_id)
            
            # الحصول على محتوى الرسالة
            message_content = db.get_pending_message_content(message_id)
            
            if message_content:
                try:
                    # نشر الرسالة في القناة مرة واحدة فقط
                    sent_message = await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_content}\n\n💡 *تم الإرسال عبر بوت المراسلة المجهولة*",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # تحديث حالة الرسالة إلى منشورة
                    db.approve_message(message_id)
                    
                    # تحديث الرسالة في المحادثة
                    try:
                        await query.edit_message_text(
                            f"✅ *تم نشر الرسالة بنجاح!*\n\n"
                            f"المحتوى: {message_content[:100]}...",
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("📋 عرض الرسائل المعلقة", callback_data="pending_messages")
                            ]])
                        )
                    except:
                        pass
                    
                    # انتظار قصير
                    await asyncio.sleep(1)
                    
                    # عرض الرسالة المعلقة التالية
                    await show_next_pending_message(query, context)
                    
                except Exception as e:
                    logger.error(f"Error posting to channel: {e}")
                    # فك القفل في حالة الفشل
                    db.unlock_message(message_id)
                    await query.answer("❌ فشل النشر. تأكد من صلاحيات البوت في القناة!", show_alert=True)
            else:
                await query.answer("❌ الرسالة غير موجودة!", show_alert=True)
        
        # رفض رسالة للقناة
        elif callback_data.startswith("reject_"):
            if not await is_admin(user_id):
                await query.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)
                return
            
            message_id = int(callback_data.replace("reject_", ""))
            
            # التحقق من أن هذه هي الرسالة المعروضة حالياً
            current_pending_id = context.user_data.get('current_pending_id')
            if current_pending_id and current_pending_id != message_id:
                await query.answer("⚠️ هذه ليست الرسالة المعروضة حالياً!", show_alert=True)
                return
            
            # التحقق مما إذا كانت الرسالة لا تزال معلقة
            if not db.is_message_pending(message_id):
                await query.answer("⚠️ هذه الرسالة تمت معالجتها بالفعل!", show_alert=True)
                await show_next_pending_message(query, context)
                return
            
            # منع المعالجة المتكررة
            db.lock_message(message_id)
            
            # رفض الرسالة
            db.reject_message(message_id)
            
            # تحديث الرسالة في المحادثة
            try:
                await query.edit_message_text(
                    "❌ *تم رفض الرسالة*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 عرض الرسائل المعلقة", callback_data="pending_messages")
                    ]])
                )
            except:
                pass
            
            await asyncio.sleep(1)
            
            # عرض الرسالة التالية
            await show_next_pending_message(query, context)
        
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
                    banned_text += f"  السبب: {user['ban_reason'] or 'غير محدد'}\n\n"
            
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
        try:
            await query.edit_message_text(
                "❌ حدث خطأ. الرجاء المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
                ]])
            )
        except:
            pass

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
    
    # إرسال للقناة (نظام المراجعة)
    if state == 'sending_to_channel':
        # التحقق من طول الرسالة
        if len(message_text) < 5:
            await update.message.reply_text("❌ الرسالة قصيرة جداً. اكتب رسالة أطول.")
            return
        
        # حفظ الرسالة كرسالة معلقة للمراجعة
        anonymous_id = db.get_anonymous_id(user_id)
        db.add_pending_message(user_id, anonymous_id, message_text)
        
        # إرسال إشعار للمشرف
        try:
            pending_count = len(db.get_pending_messages())
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📋 *رسالة جديدة للمراجعة*\n\n"
                f"📝 *المحتوى:* {message_text}\n"
                f"👤 *المرسل:* `{anonymous_id}`\n"
                f"📊 *عدد الرسائل المعلقة:* {pending_count}\n\n"
                f"استخدم لوحة المشرف للموافقة أو الرفض.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👑 فتح لوحة المشرف", callback_data="pending_messages")
                ]])
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
        
        keyboard = [
            [InlineKeyboardButton("📢 إرسال رسالة أخرى", callback_data="send_to_channel")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *تم استلام رسالتك للمراجعة!*\n\n"
            f"سيتم مراجعتها من قبل المشرف ونشرها في قناة {CHANNEL_USERNAME} قريباً.\n"
            f"شكراً لمشاركتك! 🎉",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
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
                    logger.error
