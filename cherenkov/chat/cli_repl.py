import sys
import asyncio
from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
from cherenkov.substrate.router import SubstrateRouter

def start_repl(initial_query=None, print_only=False, resume_session=None, continue_session=False):
    router = SubstrateRouter()
    memory = SQLiteConversationMemory()
    agent = QAChatAgent(memory=memory, substrate_router=router)

    session_id = None

    if resume_session:
        session = memory.get_session(resume_session)
        if session:
            session_id = resume_session
            print(f"Resumed session {session_id}")
        else:
            print(f"Session {resume_session} not found.")
            sys.exit(1)
    elif continue_session:
        sessions = memory.list_sessions(limit=1)
        if sessions:
            session_id = sessions[0].session_id
            print(f"Continued session {session_id}")
        else:
            print("No previous sessions to continue.")
            sys.exit(1)
    else:
        session = agent.create_session()
        session_id = session.session_id
        print(f"Started new session {session_id}")

    if initial_query:
        print(f"\nUser> {initial_query}")
        print("Agent> ", end="")
        asyncio.run(_stream_response(agent, session_id, initial_query))
        if print_only:
            return

    if print_only and not initial_query:
        print("Error: -p/--print requires an initial query.")
        sys.exit(1)

    print("\n\n" + "="*50)
    print("CHERENKOV Interactive QA Agent")
    print("Commands: /exit, /quit, /help, /history")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input("User> ")
            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input in ("/exit", "/quit"):
                print("Exiting session.")
                break
            elif user_input == "/help":
                print("Commands: /exit, /quit, /help, /history")
                continue
            elif user_input == "/history":
                messages = memory.get_messages(session_id)
                for msg in messages:
                    print(f"[{msg.timestamp}] {msg.role.capitalize()}: {msg.content}")
                continue

            print("Agent> ", end="")
            asyncio.run(_stream_response(agent, session_id, user_input))
            print("\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting session.")
            break

async def _stream_response(agent, session_id, user_input):
    try:
        async for token in agent.chat_stream(session_id, user_input):
            print(token, end="", flush=True)
    except Exception as e:
        print(f"\nError from agent: {e}")
