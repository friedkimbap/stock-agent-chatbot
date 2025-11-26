from strands import Agent, tool
from strands_tools import retrieve
import sys
import os
import io
# Tavily API(strands와 잘 어울리는 크롤링 API)
from tavily import TavilyClient

STOCK_AGENT_PROMPT = """당신은 전문 주식 투자 어드바이저입니다. 주식 시장 분석, 기업 정보, 투자 전략에 대한 질문에 답변해주세요.

질문에 답변하기 위해 다음 순서로 도구를 사용하세요:

1. **retrieve 도구를 우선적으로 사용하세요**: Knowledge Base에 저장된 주식 투자 자료, 기업 분석 리포트, 투자 전략 문서를 검색할 때는 반드시 retrieve 도구를 사용하세요. 질문과 관련된 투자 정보를 찾기 위해 retrieve 도구를 먼저 호출하세요.

2. **인터넷 검색 (Tavily)**: Knowledge Base에서 정보를 찾을 수 없거나 최신 시장 동향, 실시간 뉴스가 필요할 때는 `tavily_search` 도구를 사용하세요. 주가 변동, 기업 공시, 시장 뉴스 등 최신 정보를 검색합니다.

3. **기업 정보 조회**: 특정 기업에 대한 상세 정보가 필요할 때는 `get_stock_info` 도구를 사용하세요.

중요 사항:
- 투자 관련 질문이 있을 때는 항상 먼저 retrieve 도구를 사용하여 Knowledge Base에서 관련 자료를 검색하세요.
- 답변 시 투자는 본인의 판단과 책임 하에 이루어져야 함을 명시하세요.
- 구체적인 매수/매도 추천보다는 분석과 정보 제공에 집중하세요.
- 투자에 문외한인 사람이 이해하기 쉽도록 말해주세요.
- 만약 Tavily를 사용할 경우에 한국 주식이 아니면 영어로 검색을 해서 정보를 가져오세요
"""


@tool
def tavily_search(query: str) -> str:
    """Tavily API를 사용하여 웹에서 주식 및 투자 관련 정보를 검색합니다.

    최신 주식 뉴스, 시장 동향, 기업 공시, 경제 뉴스 등을 검색할 때 유용합니다.

    https://www.kbsec.com/go.able?linkcd=m04010009와 같은 링크에서 클로링하는 것이 좋을 것 같습니다.
    
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

    kb_id = os.environ.get("KNOWLEDGE_BASE_ID", "YOUR_KNOWLEDGE_BASE_ID")
    os.environ["KNOWLEDGE_BASE_ID"] = kb_id
    
    # Tavily API Key 설정
    os.environ["TAVILY_API_KEY"] = "YOUR_TAVILY_API_KEY"
    
    stock_agent = Agent(
        model="us.amazon.nova-lite-v1:0",
        system_prompt=STOCK_AGENT_PROMPT,
        tools=[get_stock_info, retrieve, tavily_search]
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