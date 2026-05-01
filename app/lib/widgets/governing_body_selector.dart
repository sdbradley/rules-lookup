import 'package:flutter/material.dart';

import '../models/governing_body.dart';

class GoverningBodySelector extends StatelessWidget {
  const GoverningBodySelector({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  final GoverningBody? selected;
  final ValueChanged<GoverningBody?> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonHideUnderline(
      child: DropdownButton<GoverningBody?>(
        value: selected,
        isDense: true,
        borderRadius: BorderRadius.circular(8),
        items: [
          const DropdownMenuItem(value: null, child: Text('All Rulebooks')),
          ...GoverningBody.values.map(
            (b) => DropdownMenuItem(value: b, child: Text(b.displayName)),
          ),
        ],
        onChanged: onChanged,
      ),
    );
  }
}
