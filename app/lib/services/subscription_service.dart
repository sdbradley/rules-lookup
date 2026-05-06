import 'package:purchases_flutter/purchases_flutter.dart';

const _revenueCatApiKey = 'appl_bQSmbmEpIGBYDKBkGEDWeXJXDaX';
const _offeringId = 'rulesai_default';
const _entitlementId = 'unlimited';

class SubscriptionService {
  static Future<void> initialize(String uid) async {
    await Purchases.setLogLevel(LogLevel.error);
    await Purchases.configure(PurchasesConfiguration(_revenueCatApiKey));
    await Purchases.logIn(uid);
  }

  static Future<bool> isSubscribed() async {
    final info = await Purchases.getCustomerInfo();
    return info.entitlements.active.containsKey(_entitlementId);
  }

  static Future<Offering?> getOffering() async {
    final offerings = await Purchases.getOfferings();
    return offerings.getOffering(_offeringId) ?? offerings.current;
  }

  static Future<bool> purchase(Package package) async {
    final result = await Purchases.purchase(PurchaseParams.package(package));
    return result.customerInfo.entitlements.active.containsKey(_entitlementId);
  }

  static Future<bool> restorePurchases() async {
    final info = await Purchases.restorePurchases();
    return info.entitlements.active.containsKey(_entitlementId);
  }
}
