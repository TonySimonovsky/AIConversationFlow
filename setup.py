from setuptools import setup, find_packages

setup(
    name='aiconversationflow',
    version='0.0.4',
    packages=find_packages(),
    description='AI Conversation Flow provides a framework for managing complex non-linear LLM conversation flows, that are composable, controllable and easily testable.',
    author='Tony AI Champ',
    author_email='tony@aicha.mp',
    url='https://aicha.mp',
    install_requires=[
        'plotly'
    ],
)
