"""
测试报告生成配置
使用 pytest-html 和 pytest-cov 生成测试报告
"""

import pytest
import os


def pytest_configure(config):
    """配置测试报告"""
    # HTML 报告配置
    config._html = os.path.join(
        os.path.dirname(__file__),
        '..',
        'reports',
        'html'
    )

    # 配置自定义 HTML 模板（可选）
    # config.option.htmlpath = 'custom_report.html'


def pytest_html_results_summary(prefix, summary, passed, failed, skipped, total):
    """自定义 HTML 报告摘要"""
    summary_str = f"""
    <div class="summary">
        <h2>测试执行摘要</h2>
        <table>
            <tr><td>总用例数</td><td>{total}</td></tr>
            <tr><td>通过</td><td class="passed">{passed}</td></tr>
            <tr><td>失败</td><td class="failed">{failed}</td></tr>
            <tr><td>跳过</td><td class="skipped">{skipped}</td></tr>
        </table>
        <p>通过率: {passed / total * 100:.1f}%</p>
    </div>
    """
    return summary_str


# 测试完成后的钩子
def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后的处理"""
    print("\n" + "="*60)
    print("测试执行完成")
    print("="*60)
    print(f"退出码: {exitstatus}")
    print(f"测试报告: reports/html/index.html")
    print(f"覆盖率报告: htmlcov/index.html")
    print("="*60)
