# Deployment status

Cloud URL: https://baandee-quality-studio.streamlit.app/
Source repository: https://github.com/67011216034-sudo/baandee-product-quality
Branch: main
Main file: streamlit_app.py
Python: 3.12

Verified on 2026-10-26 (Asia/Bangkok): Community Cloud deployed the app and displayed the native BaanDee login and registration screen at the Cloud URL.

Cloud starts from the committed source datasets and a new account database. The local working SQLite database and local accounts were not uploaded. SQLite files inside the Cloud runtime are not a long-term storage guarantee across reboot/redeploy. Export results before maintenance; see STREAMLIT_MIGRATION.md for persistent-backend planning.

Local automated validation: 10 system/API tests + 9 auth/account tests + 5 Streamlit AppTest cases. Cloud browser verification confirms the login screen; end-to-end Cloud account/CRUD behavior has not been separately claimed.
