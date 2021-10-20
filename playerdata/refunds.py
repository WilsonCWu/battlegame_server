from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from google.oauth2 import service_account
from googleapiclient.discovery import build

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata import constants, chapter_rewards_pack
from playerdata.models import PurchasedTracker
from playerdata.purchases import get_deal_from_purchase_id


def refund_purchase(purchase: PurchasedTracker):
    if purchase.purchase_id.startswith('com.salutationstudio.tinytitans.gems'):
        purchase.user.inventory.gems -= constants.IAP_GEMS_AMOUNT[purchase.purchase_id]
        purchase.user.inventory.save()

    # TODO(0.5.0): update the refund if we give not just gems in deals
    elif purchase.purchase_id.startswith('com.salutationstudio.tinytitans.deal'):
        try:
            deal = get_deal_from_purchase_id(purchase.purchase_id)
        except ObjectDoesNotExist:
            return  # invalid deal

        purchase.user.inventory.gems -= deal.base_deal.gems
        purchase.user.inventory.save()

    elif purchase.purchase_id.startswith('com.salutationstudio.tinytitans.chapterrewards'):
        chapter_rewards_pack.refund_chapter_pack(purchase.user)

    # TODO(0.5.0): figure out when we define rewards
    elif purchase.purchase_id.startswith('com.salutationstudio.tinytitans.worldpack'):
        pass

    # TODO(0.5.0): figure out when we define rewards
    elif purchase.purchase_id.startswith('com.salutationstudio.tinytitans.monthlypass'):
        pass


# https://developers.google.com/android-publisher/voided-purchases
# Runs daily and checks for refunded purchases in the past 30 days (Google's max range)
@atomic
def google_refund_cron():
    SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('androidpublisher', 'v3', credentials=credentials)
    bundle_id = 'com.salutationstudio.tinytitans'

    response = service.purchases().voidedpurchases().list(packageName=bundle_id).execute()

    refund_ids = []
    # Exit early if no refunds exist
    if 'voidedPurchases' not in response:
        return

    for purchase in response['voidedPurchases']:
        refund_ids.append(purchase['orderId'])

    refund_items = PurchasedTracker.objects.filter(transaction_id__in=refund_ids, is_refunded=False) \
        .select_related('user__inventory').select_related('user__chapterrewardpack')

    for item in refund_items:
        item.is_refunded = True
        # revoke the proper gems / award based on type of item
        refund_purchase(item)

    PurchasedTracker.objects.bulk_update(refund_items, ['is_refunded'])
