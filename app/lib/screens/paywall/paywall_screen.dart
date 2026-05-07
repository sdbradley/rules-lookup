import 'package:flutter/material.dart';
import 'package:purchases_flutter/purchases_flutter.dart';

import '../../services/subscription_service.dart';

class PaywallScreen extends StatefulWidget {
  const PaywallScreen({super.key});

  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> {
  Offering? _offering;
  bool _isLoading = true;
  bool _isPurchasing = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadOffering();
  }

  Future<void> _loadOffering() async {
    try {
      final offering = await SubscriptionService.getOffering();
      setState(() {
        _offering = offering;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Could not load subscription options. Please try again.';
        _isLoading = false;
      });
    }
  }

  Future<void> _purchase(Package package) async {
    setState(() {
      _isPurchasing = true;
      _errorMessage = null;
    });
    try {
      final success = await SubscriptionService.purchase(package);
      if (success && mounted) Navigator.of(context).pop(true);
    } on PurchasesErrorCode catch (e) {
      if (e != PurchasesErrorCode.purchaseCancelledError) {
        setState(() => _errorMessage = 'Purchase failed. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _isPurchasing = false);
    }
  }

  Future<void> _restore() async {
    setState(() => _isPurchasing = true);
    try {
      final success = await SubscriptionService.restorePurchases();
      if (mounted) {
        if (success) {
          Navigator.of(context).pop(true);
        } else {
          setState(() => _errorMessage = 'No active subscription found.');
        }
      }
    } finally {
      if (mounted) setState(() => _isPurchasing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _buildContent(),
    );
  }

  Widget _buildContent() {
    final packages = _offering?.availablePackages ?? [];

    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(
          24, 16, 24, MediaQuery.of(context).padding.bottom + 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Image.asset('assets/logo.png', height: 64),
          const SizedBox(height: 16),
          Text.rich(
            TextSpan(
              text: 'Unlimited Rules',
              children: [
                TextSpan(
                  text: 'AI',
                  style: const TextStyle(color: Color(0xFF2D7FE6)),
                ),
              ],
            ),
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'You\'ve used all 20 free queries this month.',
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: Colors.grey),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          const _FeatureRow(icon: Icons.all_inclusive, text: 'Look up as many rules as you want'),
          const _FeatureRow(icon: Icons.menu_book, text: 'Access to all rulebooks'),
          const _FeatureRow(icon: Icons.cancel_outlined, text: 'Cancel anytime'),
          const SizedBox(height: 32),
          if (_errorMessage != null) ...[
            Text(_errorMessage!,
                style: const TextStyle(color: Colors.red),
                textAlign: TextAlign.center),
            const SizedBox(height: 16),
          ],
          if (packages.isEmpty)
            const Text('No subscription options available.',
                textAlign: TextAlign.center)
          else
            ...packages.map((p) => _PackageButton(
                  package: p,
                  isPurchasing: _isPurchasing,
                  onTap: () => _purchase(p),
                )),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _isPurchasing ? null : _restore,
            child: const Text('Restore purchases'),
          ),
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _PackageButton extends StatelessWidget {
  const _PackageButton({
    required this.package,
    required this.isPurchasing,
    required this.onTap,
  });

  final Package package;
  final bool isPurchasing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final product = package.storeProduct;
    final isAnnual = package.packageType == PackageType.annual;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: FilledButton(
        onPressed: isPurchasing ? null : onTap,
        style: isAnnual
            ? null
            : FilledButton.styleFrom(
                backgroundColor:
                    Theme.of(context).colorScheme.secondaryContainer,
                foregroundColor:
                    Theme.of(context).colorScheme.onSecondaryContainer,
              ),
        child: isPurchasing
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(strokeWidth: 2))
            : Column(
                children: [
                  const SizedBox(height: 4),
                  Text(
                    isAnnual ? 'Annual — ${product.priceString}/year' : 'Monthly — ${product.priceString}/month',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  if (isAnnual)
                    Text(
                      'Best value — save ~40%',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onPrimary
                                .withValues(alpha: 0.8),
                          ),
                    ),
                  const SizedBox(height: 4),
                ],
              ),
      ),
    );
  }
}
