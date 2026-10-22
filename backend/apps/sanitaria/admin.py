# Health data is deliberately NOT registered in the Django admin: the admin would bypass
# the access log (DEC-101) and the technical administrator must not see educational or
# health data (DEC-12). Everything goes through the API and its policy checks.
