# this script is run to deploy app on render

if __name__ == '__main__':
    import os

    from oh_sched_web.app import app

    print('hello from render.py')

    # Get port from environment variable (default to 5000 for local dev)
    port = os.environ.get('PORT', 5000)

    print(f'os.environ: {os.environ}')

    # Bind to 0.0.0.0 to accept external requests
    app.run(host='0.0.0.0', port=port)
