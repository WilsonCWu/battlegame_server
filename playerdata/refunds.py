from django.db.transaction import atomic
from google.oauth2 import service_account
from googleapiclient.discovery import build

from battlegame.settings import SERVICE_ACCOUNT_FILE
from playerdata.models import PurchasedTracker


def refund_purchase(purchase: PurchasedTracker):
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
    for purchase in response['voidedPurchases']:
        refund_ids.append(purchase['orderId'])

    refund_items = PurchasedTracker.objects.filter(purchase_id__in=refund_ids, is_refunded=False).select_related('user__inventory')
    for item in refund_items:
        item.is_refunded = True
        # revoke the proper gems / award based on type of item
        refund_purchase(item)

    PurchasedTracker.objects.bulk_update(refund_items, ['is_refunded'])
