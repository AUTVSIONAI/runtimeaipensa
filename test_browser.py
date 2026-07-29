import asyncio
from runtime.config import RuntimeConfig
from runtime.runtime import create_runtime

async def test():
    config = RuntimeConfig.from_toml('runtime.toml')
    rt = await create_runtime(config)
    print('Modules loaded:', list(rt.modules.keys()))

    browser = rt.get_browser()
    if browser:
        print('Browser module state:', browser.state)
        # Create a session
        session = await browser.create_session('https://example.com')
        print('Session created:', session.session_id)

        # Get state
        state = await browser.get_state(session.session_id)
        print('URL:', state.url)
        print('Title:', state.title)

        # Test click by selector
        result = await browser.execute_action(session.session_id, 'click', {'selector': 'h1'})
        print('Click result:', result)

        # Test type by selector
        result = await browser.execute_action(session.session_id, 'type', {'selector': 'input', 'text': 'Hello World'})
        print('Type result:', result)

        # Take screenshot
        screenshot = await browser.take_screenshot(session.session_id, True)
        print('Screenshot length:', len(screenshot) if screenshot else 0)

        await browser.close_session(session.session_id)

    await rt.stop()

asyncio.run(test())