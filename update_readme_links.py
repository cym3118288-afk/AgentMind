#!/usr/bin/env python3
"""
自动更新 README.md 中的文档链接
执行 reorganize_files 后运行此脚本
"""

import re
import os
from pathlib import Path


def update_readme_links(readme_path='README.md'):
    """更新 README.md 中的文档链接"""

    if not os.path.exists(readme_path):
        print(f"❌ 错误: {readme_path} 不存在")
        return False

    print(f"📖 读取 {readme_path}...")
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 定义替换规则 - 从根目录到新位置
    replacements = {
        # API 文档
        r'\(API\.md\)': '(docs/api/API.md)',
        r'\(ARCHITECTURE\.md\)': '(docs/api/ARCHITECTURE.md)',

        # 指南文档
        r'\(TROUBLESHOOTING\.md\)': '(docs/guides/TROUBLESHOOTING.md)',
        r'\(FAQ\.md\)': '(docs/guides/FAQ.md)',
        r'\(QUICKSTART\.md\)': '(docs/guides/QUICKSTART.md)',
        r'\(QUICK_REFERENCE\.md\)': '(docs/guides/QUICK_REFERENCE.md)',
        r'\(ADVANCED_FEATURES\.md\)': '(docs/guides/ADVANCED_FEATURES.md)',
        r'\(PERFORMANCE\.md\)': '(docs/guides/PERFORMANCE.md)',
        r'\(PERFORMANCE_IMPLEMENTATION\.md\)': '(docs/guides/PERFORMANCE_IMPLEMENTATION.md)',
        r'\(SCALING\.md\)': '(docs/guides/SCALING.md)',
        r'\(MIGRATION\.md\)': '(docs/guides/MIGRATION.md)',
        r'\(COMPARISON\.md\)': '(docs/guides/COMPARISON.md)',
        r'\(EXAMPLES\.md\)': '(docs/guides/EXAMPLES.md)',
        r'\(EXAMPLES_INDEX\.md\)': '(docs/guides/EXAMPLES_INDEX.md)',
        r'\(CHAT_README\.md\)': '(docs/guides/CHAT_README.md)',
        r'\(DEVELOPER_TOOLS\.md\)': '(docs/guides/DEVELOPER_TOOLS.md)',

        # 部署文档
        r'\(DEPLOYMENT\.md\)': '(docs/deployment/DEPLOYMENT.md)',
        r'\(DOCKER\.md\)': '(docs/deployment/DOCKER.md)',
        r'\(RELEASING\.md\)': '(docs/deployment/RELEASING.md)',
        r'\(WAVE3_PRODUCTION_READINESS\.md\)': '(docs/deployment/WAVE3_PRODUCTION_READINESS.md)',

        # 发布说明
        r'\(RELEASE_NOTES_v0\.3\.0\.md\)': '(docs/RELEASE_NOTES_v0.3.0.md)',
        r'\(RELEASE_NOTES_v0\.4\.0\.md\)': '(docs/RELEASE_NOTES_v0.4.0.md)',

        # 贡献者
        r'\(CONTRIBUTORS\.md\)': '(docs/CONTRIBUTORS.md)',
    }

    # 执行替换
    changes_made = 0
    for pattern, replacement in replacements.items():
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            changes_made += matches
            print(f"  ✓ 替换 {matches} 个链接: {pattern} → {replacement}")

    if content == original_content:
        print("ℹ️  没有需要更新的链接")
        return True

    # 写回文件
    print(f"\n💾 保存更新到 {readme_path}...")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 成功更新 {changes_made} 个链接")
    return True


def verify_links(readme_path='README.md'):
    """验证 README.md 中的所有本地链接"""

    print(f"\n🔍 验证 {readme_path} 中的链接...")

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有 markdown 链接
    links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)

    broken = []
    valid = 0

    for text, link in links:
        # 跳过外部链接
        if link.startswith(('http://', 'https://', 'mailto:')):
            continue

        # 跳过锚点
        if link.startswith('#'):
            continue

        # 检查文件是否存在
        if os.path.exists(link):
            valid += 1
        else:
            broken.append((text, link))

    print(f"\n📊 链接验证结果:")
    print(f"  ✅ 有效链接: {valid}")
    print(f"  ❌ 损坏链接: {len(broken)}")

    if broken:
        print(f"\n❌ 发现 {len(broken)} 个损坏的链接:")
        for text, link in broken:
            print(f"  - [{text}]({link})")
        return False
    else:
        print("\n✅ 所有本地链接都有效!")
        return True


def main():
    """主函数"""
    print("=" * 60)
    print("AgentMind README 链接更新工具")
    print("=" * 60)
    print()

    # 检查是否在正确的目录
    if not os.path.exists('README.md'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        return 1

    # 更新链接
    if not update_readme_links():
        return 1

    # 验证链接
    if not verify_links():
        print("\n⚠️  警告: 发现损坏的链接，请检查文件是否已正确移动")
        return 1

    print("\n" + "=" * 60)
    print("✅ 所有操作完成!")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 检查 git diff README.md")
    print("  2. 运行: git add README.md")
    print("  3. 运行: git commit -m 'docs: update documentation links'")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
