# PLODA Member Portal

A professional full-stack member portal for the People's Land Ownership and Development Association. The portal is built with a responsive browser interface, a Python server, persistent SQLite records and secure server-side sessions.

## Included pages

The public landing page leads to account creation and sign-in. Authenticated members receive access to:

1. Dashboard
2. Projects
3. My payments
4. Deposit funds
5. Statements
6. Documents
7. News & updates
8. Support chat
9. Profile
10. Constitution
11. Member registration

## Security controls

- Passwords require at least 10 characters with uppercase, lowercase, a number and a special character.
- Passwords are stored using PBKDF2-HMAC-SHA256 with a unique salt and 310,000 iterations.
- Authentication uses random, server-side, expiring sessions in HttpOnly, SameSite cookies.
- State-changing requests use a CSRF token.
- Sign-in attempts are rate limited.
- SQL statements are parameterised.
- Security headers include a strict content security policy, frame protection and HSTS in production.
- The portal does not collect or store Visa card numbers or one-time passwords.

## Run locally

```bash
python3 app.py
```

Open `http://localhost:8080`. Create an account through the landing page. The database is created automatically under `data/ploda.db`.

Run the automated production checks with:

```bash
python3 -m unittest discover -s tests -v
```

The GitHub workflow in `.github/workflows/ci.yml` repeats these tests and builds the production container for every proposed or published change.

## Production deployment for ploda.org

1. Push the project to a GitHub repository using the `main` branch.
2. Deploy the repository with the supplied `render.yaml` Blueprint. It defines the Docker service, `/health` monitoring, a persistent disk mounted at `/data`, and automatic deployment only after GitHub checks pass.
3. Review and approve the hosting plan before creating the service because persistent storage is required for member and payment records.
4. Add live payment and bank values through the hosting provider's protected environment settings. Do not put them in GitHub.
5. Configure `ploda.org` and `www.ploda.org` using the DNS values supplied after the service is created.
6. Enable HTTPS and redirect HTTP traffic to HTTPS.
7. Confirm that `/health` returns a successful response before opening access to members.

For another hosting provider, deploy the project with the supplied `Dockerfile` and provide a persistent disk mounted at `/data`.

If Cloudflare manages the domain, create the DNS record required by the selected hosting provider, enable proxying only after origin verification, and use Full (strict) TLS mode with a valid origin certificate.

## Live payment configuration

Payment buttons are active only after the corresponding protected environment values are configured.

- **Bank transfer:** set the bank name, account name, account number and branch.
- **EcoCash:** set the merchant API URL, API key, merchant ID and webhook secret supplied by the approved EcoCash merchant service or payment service provider.
- **Visa:** set `VISA_CHECKOUT_URL` to a PCI-compliant hosted checkout page supplied by the acquiring bank or payment service provider. Card numbers must never be collected by this portal.
- **PayPal:** set the live PayPal client ID and secret, and retain `PAYPAL_MODE=live`.
- **Cash:** cash requests are recorded as awaiting verification and should be completed only at an authorised PLODA office against an official receipt.

Before launch, perform low-value live tests for every configured channel, reconcile each provider result to the portal reference and confirm refund and failed-payment handling with the merchant provider.

## Important launch note

`PLODA_Constitution_Portal_Reference.pdf` is deliberately identified as a portal reference. Replace it with the signed legal master constitution before relying on it as PLODA's authoritative legal instrument.
