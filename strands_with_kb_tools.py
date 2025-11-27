from strands import Agent, tool
from strands_tools import retrieve
import sys
import os
import io
from dotenv import load_dotenv
# Tavily API(strands와 잘 어울리는 크롤링 API)
from tavily import TavilyClient

STOCK_AGENT_PROMPT = """당신은 전문 주식 투자 어드바이저입니다. 주식 시장 분석, 기업 정보, 투자 전략에 대한 질문에 답변해주세요.

**필수 규칙 - 반드시 따라야 합니다!**

**STEP 1: 모든 질문에 대해 무조건 retrieve 도구를 먼저 호출하세요!**
- 어떤 질문이든 상관없이 retrieve 도구를 가장 먼저 사용해야 합니다.
- retrieve 도구로 Knowledge Base를 검색하지 않고 답변하는 것은 절대 금지입니다.
- 기업명, 주식, 투자 관련 키워드가 있으면 반드시 retrieve로 검색하세요.

**STEP 2: retrieve 결과 확인**
- retrieve에서 관련 정보를 찾았다면, 그 정보를 기반으로 답변하세요.
- retrieve에서 정보를 찾지 못했거나 최신 정보가 필요한 경우에만 tavily_search를 사용하세요.
- https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521 사이트에서 우선적으로 크롤링해오세요

**STEP 3: 추가 정보가 필요한 경우**
- 최신 뉴스, 실시간 주가가 필요하면 tavily_search를 사용하세요.
- 한국 주식이 아닌 경우 영어로 검색하세요.

**절대 규칙:**
- 스스로 판단하거나 추측하지 마세요
- 도구를 사용하지 않고 일반적인 정보만 제공하지 마세요
- 항상 retrieve → (필요시) tavily_search 순서로 진행하세요
- 답변은 무조건 한국어로 하세요
- 투자 초보자도 이해할 수 있게 쉽게 설명하세요
- 답변 마지막에 "투자는 본인의 판단과 책임 하에 이루어져야 합니다" 문구를 포함하세요
"""


@tool
def tavily_search(query: str) -> str:
    """Tavily API를 사용하여 웹에서 주식 및 투자 관련 정보를 검색합니다.

    최신 주식 뉴스, 시장 동향, 기업 공시, 경제 뉴스 등을 검색할 때 유용합니다.
    
    Args:
        query: 검색할 키워드나 질문 (예: "삼성전자 최근 뉴스", "반도체 시장 전망")
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return "오류: TAVILY_API_KEY 환경 변수가 설정되지 않았습니다."
        
    try:
        tavily = TavilyClient(api_key=tavily_key)
        # search_depth="advanced"로 설정하면 더 깊이 있는 검색 결과를 제공합니다.
        response = tavily.search(query=query, search_depth="advanced")
        
        # 결과를 문자열로 포맷팅
        results = []
        for result in response.get('results', []):
            title = result.get('title', 'No Title')
            url = result.get('url', 'No URL')
            content = result.get('content', 'No Content')
            results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n---")
            
        return "\n".join(results)
    except Exception as e:
        return f"Tavily 검색 중 오류 발생: {str(e)}"


@tool
def get_stock_info(company_name: str) -> str:
    """특정 기업의 주식 정보와 최근 뉴스를 검색합니다.
    
    Args:
        company_name: 기업명 (예: "삼성전자", "Apple", "Tesla")
    """
    # Tavily를 사용하여 기업 정보 검색
    search_query = f"{company_name} 주가 실적 뉴스 분석"
    return tavily_search(search_query)


def safe_input(prompt: str) -> str:
    """UTF-8 인코딩 오류를 안전하게 처리하는 input 함수."""
    try:
        # 먼저 일반 input 시도
        return input(prompt).strip()
    except UnicodeDecodeError:
        # 인코딩 오류 발생 시 재시도
        try:
            # stdin을 UTF-8로 재설정
            if hasattr(sys.stdin, 'buffer'):
                sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
            return input(prompt).strip()
        except (UnicodeDecodeError, UnicodeError):
            # 그래도 실패하면 raw bytes로 읽기
            try:
                sys.stdout.write(prompt)
                sys.stdout.flush()
                line = sys.stdin.buffer.readline()
                return line.decode('utf-8', errors='replace').strip()
            except Exception:
                raise


def main():
    """Main function to run the stock investment advisor agent as a script."""
    
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # Knowledge Base ID와 Tavily API Key 확인
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    
    if not kb_id:
        print("⚠️ 경고: KNOWLEDGE_BASE_ID가 .env 파일에 설정되지 않았습니다.")
        print("Knowledge Base 검색 기능이 작동하지 않을 수 있습니다.\n")
    
    if not tavily_key:
        print("⚠️ 경고: TAVILY_API_KEY가 .env 파일에 설정되지 않았습니다.")
        print("인터넷 검색 기능이 작동하지 않을 수 있습니다.\n")
    
    stock_agent = Agent(
        model="us.amazon.nova-lite-v1:0",
        system_prompt=STOCK_AGENT_PROMPT,
        tools=[retrieve, tavily_search, get_stock_info]
    )
    
    # Command line argument이 있으면 한 번만 실행하고 종료
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        try:
            response = stock_agent(prompt)
            print(response)
        except UnicodeDecodeError as e:
            print(f"인코딩 오류가 발생했습니다: {e}")
            print("응답을 처리하는 중 문제가 발생했습니다.")
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
        return
    
    # 대화형 모드: 사용자가 "종료" 또는 "exit"를 입력할 때까지 계속 실행
    print("=" * 60)
    print("🔹 주식 투자 어드바이저 챗봇을 시작합니다 🔹")
    print("=" * 60)
    print("\n💡 사용 가능한 질문 예시:")
    print("  - 삼성전자 최근 주가 동향은?")
    print("  - 반도체 산업 전망 분석해줘")
    print("  - 테슬라 실적 발표 내용 알려줘")
    print("  - AI 관련 주식 추천해줘")
    print("\n  투자 책임은 본인에게 있습니다.")
    print("종료하려면 '종료' 또는 'exit'를 입력하세요.\n")
    print("=" * 60 + "\n")
    
    while True:
        try:
            prompt = safe_input("질문을 입력하세요: ")
            
            # 종료 조건 확인
            if prompt.lower() in ['종료', 'exit', 'quit', 'q']:
                print("\n주식 투자 어드바이저를 종료합니다. 성공적인 투자 되세요!")
                break
            
            # 빈 입력 처리
            if not prompt:
                print("질문을 입력해주세요.\n")
                continue
            
            # 에이전트 실행
            try:
                print("\n🔍 분석 중...\n")
                response = stock_agent(prompt)
                print(f"답변:\n{response}\n")
                print("=" * 60 + "\n")
            except UnicodeDecodeError as e:
                print(f"\n인코딩 오류가 발생했습니다: {e}")
                print("응답을 처리하는 중 문제가 발생했습니다. 다시 시도해주세요.\n")
            except Exception as e:
                print(f"\n오류가 발생했습니다: {e}\n")
                
        except KeyboardInterrupt:
            print("\n\n주식 투자 어드바이저를 종료합니다. 성공적인 투자 되세요! 📈")
            break
        except EOFError:
            print("\n\n주식 투자 어드바이저를 종료합니다. 성공적인 투자 되세요! 📈")
            break


if __name__ == "__main__":
    main()