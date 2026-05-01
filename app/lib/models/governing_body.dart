enum GoverningBody {
  dyb('DYB', 'Diamond Youth Baseball'),
  dys('DYS', 'Diamond Youth Softball'),
  obr('OBR', 'Official Baseball Rules'),
  nfhsSoftball('NFHS_SOFTBALL', 'NFHS Softball');

  const GoverningBody(this.apiValue, this.displayName);

  final String apiValue;
  final String displayName;
}
