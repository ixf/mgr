from ..runner import Runner
from ..mock_runner import MockRunner
from pandas.testing import assert_frame_equal

async def test_mock_compare():
    df = await Runner('test_zip', workers='workers_tests.yml').run()
    dfm = MockRunner(df, None, 'zip').run()

    to_drop = ['timestamp', 'full_read']
    df = df.drop(columns=to_drop)
    dfm = dfm.drop(columns=to_drop)

    assert_frame_equal(df, dfm, check_like=True)
