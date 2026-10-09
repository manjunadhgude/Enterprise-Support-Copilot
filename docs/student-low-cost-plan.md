# Student-friendly, low-cost project plan

This project can be developed and demonstrated locally without paying for cloud hosting or model API calls. Treat cloud deployment as an optional later phase, and check current service terms and prices before creating resources.

## Phase 1: no-cloud development

- Run the app on your own computer with its local SQLite database and synthetic demo data.
- Keep deterministic/mock behavior for demonstrations; do not add an API key just to make the app runnable.
- Use the repository's GitHub Actions workflow for automated checks after the project is placed in a GitHub repository. GitHub's plan limits and usage terms apply.
- Never commit `.env`, `.env.local`, database files, real company data, or API credentials. The project `.gitignore` excludes these local files.

## Phase 2: optional student cloud demo

If you qualify for Azure for Students, check the current offer and account terms first. Microsoft currently advertises USD $100 in credit for 12 months, selected free service amounts, and no credit card at signup. Eligibility and included services are limited and can change. When the credit is exhausted, the student subscription is disabled unless you choose to upgrade.

For a small demo, investigate these options before provisioning:

- Azure Container Apps Consumption can scale to zero. It currently includes monthly free usage grants, but usage beyond the grants, networking, logging, registries, or other attached resources may cost money.
- Azure Database for PostgreSQL has a listed student/free amount for eligible offers and periods. Verify the exact region, duration, size, backup allowance, and current availability in your account before creating a server.
- Keep the app at zero minimum replicas while idle and remove resources after a demo if you do not need them.
- Use a budget alert and inspect Cost Management regularly. A budget alert sends a notification; it does **not** automatically stop resources or guarantee a hard spending cap.
- Use the Azure pricing calculator for the actual region and chosen configuration. Do not assume the student credit covers OpenAI API usage or every Azure service.

## Suggested choice for this project

The selected plan is **local-only development**. It is enough to run and present the engineering project without cloud hosting or API spend. If a hosted demo becomes important later, use the Azure student offer only after confirming eligibility and the precise free allowances; deploy a small Container Apps Consumption instance and the smallest suitable database, and delete them when the demo is over. Keep live identity and enterprise IT integrations as later, separately costed work.

## Current blockers that require the project owner

- Verify student eligibility and activate the Azure subscription, if desired.
- Decide whether a public hosted demo is necessary; local demo remains the no-cost default.
- Select the real identity provider and ticketing/IT services only if live integration is required.
- Provide independently reviewed answer-quality judgments for trustworthy evaluation labels.
- Complete secure API credential setup only if paid model-backed generation is desired. Deterministic demo behavior can remain the default.

## Official references

- [Azure for Students](https://azure.microsoft.com/en-us/free/students/)
- [Azure for Students offer terms](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p)
- [Azure Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)
- [Azure budgets and alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
