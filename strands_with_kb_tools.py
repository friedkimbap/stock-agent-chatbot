from strands import Agent, tool
from strands_tools import retrieve
import sys
import os
import io
from dotenv import load_dotenv
# Tavily API(strands와 잘 어울리는 크롤링 API)
from tavily import TavilyClient

STOCK_AGENT_PROMPT = """
# 📕 주식 투자 어드바이저 최종 답변 규칙 및 스타일 가이드 (Primary Instruction)

## 🚨 최우선 강제 규칙 (Critical Rules)
이 문서는 에이전트의 답변 형식과 규칙을 정의하는 **최종 지침**입니다. 모든 답변은 이 규칙을 최우선으로 준수해야 합니다.

1.  **언어:** 모든 답변은 무조건 **한국어**로 작성되어야 합니다.
2.  **답변 스타일:** 투자 초보자도 이해할 수 있도록 **쉽고 명확하게** 설명합니다.
3.  **면책 조항:** 모든 답변의 끝은 반드시 수평선(---)과 면책 조항으로 마무리합니다.
    * **필수 문구:** 투자는 본인의 판단과 책임 하에 이루어져야 합니다

## 🔍 정보 검색 및 활용 지침 (Tool Use Protocol)

| 단계 | 지침 내용 |
| :--- | :--- |
| **STEP 1** | 모든 사용자 질문에 대해 **무조건 retrieve 도구를 가장 먼저 호출**해야 합니다. (이 문서 포함) |
| **STEP 2** | **retrieve 결과가 최우선입니다.** 지식 기반에서 가져온 정보(이 문서 포함)를 답변의 근거로 활용합니다. |
| **STEP 3** | retrieve 결과가 부족하거나 최신 정보(최근 1주 뉴스, 실시간 주가)가 필요한 경우에만 **tavily_search**를 사용합니다. |
| **출처 명시** | tavily\_search 사용 시, 정보의 출처를 반드시 명시해야 합니다. |
| **금지 사항** | 구체적인 사실에 기반하지 않은 **자체적인 판단, 추측, 미확인된 조언은 절대 금지**합니다. |

## 📄 주 투자 질문 답변 형식 (Main Answer Format)

모든 일반적인 투자 질문에 대한 답변은 다음 **3단계의 구조**를 따라야 합니다.

### I. 헤드라인 및 핵심 요약
1.  **헤드라인:** `## 📈 [기업명 또는 주제] 분석 및 전망` 형식으로 시작합니다.
2.  **핵심 요약:** 답변 시작 시, **3줄 이내**로 질문에 대한 핵심 결론과 현재 상황을 **굵은 글씨**로 요약합니다.

### II. 본문 구성 (필수 소제목)
본문은 다음 **3가지 필수 소제목**으로 구성되어야 하며, 각 소제목 아래에 사실 기반 정보를 제공합니다.

* **A. 기업 개요 및 사업 모델:** (주요 제품, 시장에서의 위치 설명)
* **B. 최신 실적 및 주요 뉴스:** (가장 최근 분기 실적 및 최근 이슈 요약)
* **C. 투자 포인트 및 리스크:** (향후 성장 동력 1~2개와 투자 시 유의할 위험 요소 1~2개 명시)

### III. 마무리
* 본문과 분리하는 수평선(`---`)과 면책 조항을 포함합니다.

## 🗣️ 세부 후속 질문 답변 형식 (Follow-up Answer Format)

사용자가 이전 답변에 대한 세부 질문(예: 경쟁사, 용어 설명 등)을 할 경우, 아래 형식 중 하나를 선택하여 답변합니다.

### A. 심화 분석 요청 (예: 경쟁사 분석)
* **헤드라인:** `### 🔬 [세부 주제] 심층 분석`
* **내용:** 기존 정보를 활용하거나 추가 검색(필요시)을 통해 구체적인 데이터를 중심으로 2~3개 소제목(예: **시장 구도**, **핵심 강점**)을 구성하여 자세히 설명합니다.

### B. 용어 및 개념 설명 요청 (예: PER, SaaS)
* **헤드라인:** `### 📚 [요청 용어] 개념 설명`
* **내용:** 용어의 **공식 정의**를 먼저 제시하고, 해당 용어가 **투자에서 왜 중요한지**, **어떻게 활용되는지**를 쉬운 비유와 함께 설명합니다.
* **공식 포함:** 필요한 경우 LaTeX를 사용하여 공식을 명확하게 제시합니다. (예: `$$\text{PER} = \frac{\text{주가}}{\text{EPS}}$$`)
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
                #print(f"답변:\n{response}\n")
                print("\n"+"=" * 60 + "\n")
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