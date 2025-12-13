"""
Synthetic Data Generator - Creates test cases for evaluating the multi-agent system.
"""

import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
# Import moved to avoid circular dependency - will define EvaluationCase here
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class EvaluationCase:
    """A single evaluation test case."""
    id: str
    question: str
    category: str
    difficulty: str
    context: str = ""
    expected_answer: Optional[str] = None
    ground_truth: Optional[Dict[str, Any]] = None

class SyntheticDataGenerator:
    """
    Generator for synthetic test cases to evaluate the multi-agent system.
    
    Creates diverse test cases across different categories and difficulty levels
    to comprehensively test system performance.
    """
    
    def __init__(self):
        self.factual_questions = [
            "What is the capital of {country}?",
            "Who wrote the book '{book}'?",
            "What year was {event} established?",
            "What is the chemical symbol for {element}?",
            "Who invented the {invention}?",
        ]
        
        self.conceptual_questions = [
            "Explain the difference between {concept1} and {concept2}.",
            "What are the main causes of {phenomenon}?",
            "How does {process} work?",
            "What are the advantages and disadvantages of {technology}?",
            "Describe the relationship between {concept1} and {concept2}.",
        ]
        
        self.reasoning_questions = [
            "If {condition}, what would be the likely consequences?",
            "Compare and contrast {item1} and {item2} in terms of {criteria}.",
            "What factors should be considered when {decision}?",
            "Analyze the pros and cons of {scenario}.",
            "What would happen if {hypothetical_situation}?",
        ]
        
        # Sample data for filling templates
        self.sample_data = {
            'countries': ['France', 'Japan', 'Brazil', 'Canada', 'Australia'],
            'books': ['1984', 'To Kill a Mockingbird', 'The Great Gatsby', 'Pride and Prejudice'],
            'events': ['the United Nations', 'NASA', 'the Internet', 'the European Union'],
            'elements': ['gold', 'silver', 'oxygen', 'carbon', 'hydrogen'],
            'inventions': ['telephone', 'light bulb', 'computer', 'airplane', 'printing press'],
            'concepts': ['machine learning', 'artificial intelligence', 'blockchain', 'quantum computing'],
            'phenomena': ['climate change', 'inflation', 'market volatility', 'social media addiction'],
            'processes': ['photosynthesis', 'DNA replication', 'economic recession', 'supply chain management'],
            'technologies': ['renewable energy', 'autonomous vehicles', 'virtual reality', 'gene therapy'],
            'items': ['electric cars', 'traditional cars', 'solar panels', 'wind turbines'],
            'criteria': ['cost', 'efficiency', 'environmental impact', 'scalability'],
            'decisions': ['choosing a career', 'investing in stocks', 'starting a business', 'buying a house'],
            'scenarios': ['remote work', 'universal basic income', 'space colonization', 'AI regulation'],
            'conditions': ['interest rates rise significantly', 'a new technology disrupts an industry', 'climate change accelerates'],
            'hypothetical_situations': ['all fossil fuels were banned tomorrow', 'artificial intelligence became sentient', 'teleportation was invented']
        }
    
    def generate_factual_questions(self, count: int = 10) -> List[EvaluationCase]:
        """Generate factual knowledge questions."""
        cases = []
        
        for i in range(count):
            template = random.choice(self.factual_questions)
            
            # Fill template with sample data
            if '{country}' in template:
                question = template.format(country=random.choice(self.sample_data['countries']))
            elif '{book}' in template:
                question = template.format(book=random.choice(self.sample_data['books']))
            elif '{event}' in template:
                question = template.format(event=random.choice(self.sample_data['events']))
            elif '{element}' in template:
                question = template.format(element=random.choice(self.sample_data['elements']))
            elif '{invention}' in template:
                question = template.format(invention=random.choice(self.sample_data['inventions']))
            else:
                question = template
            
            case = EvaluationCase(
                id=f"factual_{i+1}",
                question=question,
                category="Factual Knowledge",
                difficulty="Easy"
            )
            cases.append(case)
        
        return cases
    
    def generate_conceptual_questions(self, count: int = 10) -> List[EvaluationCase]:
        """Generate conceptual understanding questions."""
        cases = []
        
        for i in range(count):
            template = random.choice(self.conceptual_questions)
            
            # Fill template with sample data
            if '{concept1}' in template and '{concept2}' in template:
                concepts = random.sample(self.sample_data['concepts'], 2)
                question = template.format(concept1=concepts[0], concept2=concepts[1])
            elif '{phenomenon}' in template:
                question = template.format(phenomenon=random.choice(self.sample_data['phenomena']))
            elif '{process}' in template:
                question = template.format(process=random.choice(self.sample_data['processes']))
            elif '{technology}' in template:
                question = template.format(technology=random.choice(self.sample_data['technologies']))
            else:
                question = template
            
            case = EvaluationCase(
                id=f"conceptual_{i+1}",
                question=question,
                category="Conceptual Understanding",
                difficulty="Medium"
            )
            cases.append(case)
        
        return cases
    
    def generate_reasoning_questions(self, count: int = 10) -> List[EvaluationCase]:
        """Generate complex reasoning questions."""
        cases = []
        
        for i in range(count):
            template = random.choice(self.reasoning_questions)
            
            # Fill template with sample data
            if '{condition}' in template:
                question = template.format(condition=random.choice(self.sample_data['conditions']))
            elif '{item1}' in template and '{item2}' in template and '{criteria}' in template:
                items = random.sample(self.sample_data['items'], 2)
                criteria = random.choice(self.sample_data['criteria'])
                question = template.format(item1=items[0], item2=items[1], criteria=criteria)
            elif '{decision}' in template:
                question = template.format(decision=random.choice(self.sample_data['decisions']))
            elif '{scenario}' in template:
                question = template.format(scenario=random.choice(self.sample_data['scenarios']))
            elif '{hypothetical_situation}' in template:
                question = template.format(hypothetical_situation=random.choice(self.sample_data['hypothetical_situations']))
            else:
                question = template
            
            case = EvaluationCase(
                id=f"reasoning_{i+1}",
                question=question,
                category="Complex Reasoning",
                difficulty="Hard"
            )
            cases.append(case)
        
        return cases
    
    def generate_financial_questions(self, count: int = 5) -> List[EvaluationCase]:
        """Generate financial analysis questions using the sample database."""
        cases = []
        companies = ["TechCorp Inc", "FinanceGlobal", "HealthcarePlus", "EnergyFuture", "RetailMega"]
        years = [2020, 2021, 2022, 2023]
        
        financial_templates = [
            "Calculate the profit margin for {company} in {year} and explain what it means for investors.",
            "Compare the debt-to-revenue ratio of {company1} and {company2} in {year}.",
            "Analyze the financial performance of {company} over the period {year1}-{year2}.",
            "Which company had the best return on investment in {year} and why?",
            "What are the key financial risks for {company} based on their {year} performance?"
        ]
        
        for i in range(count):
            template = random.choice(financial_templates)
            
            if '{company1}' in template and '{company2}' in template:
                selected_companies = random.sample(companies, 2)
                year = random.choice(years)
                question = template.format(
                    company1=selected_companies[0],
                    company2=selected_companies[1],
                    year=year
                )
            elif '{year1}' in template and '{year2}' in template:
                company = random.choice(companies)
                year_range = sorted(random.sample(years, 2))
                question = template.format(
                    company=company,
                    year1=year_range[0],
                    year2=year_range[1]
                )
            else:
                company = random.choice(companies)
                year = random.choice(years)
                question = template.format(company=company, year=year)
            
            case = EvaluationCase(
                id=f"financial_{i+1}",
                question=question,
                category="Financial Analysis",
                difficulty="Medium",
                context="Use the financial database to provide accurate, data-driven analysis."
            )
            cases.append(case)
        
        return cases
    
    def generate_edge_cases(self, count: int = 5) -> List[EvaluationCase]:
        """Generate edge cases that might challenge the system."""
        edge_case_questions = [
            "What is the square root of -1?",  # Mathematical edge case
            "Explain quantum superposition to a 5-year-old.",  # Complexity mismatch
            "What will the stock market do tomorrow?",  # Unpredictable question
            "Is it ethical to lie to save someone's feelings?",  # Subjective/ethical
            "How many angels can dance on the head of a pin?",  # Nonsensical question
        ]
        
        cases = []
        for i, question in enumerate(edge_case_questions[:count]):
            case = EvaluationCase(
                id=f"edge_{i+1}",
                question=question,
                category="Edge Cases",
                difficulty="Hard"
            )
            cases.append(case)
        
        return cases
    
    def generate_comprehensive_test_suite(
        self,
        factual_count: int = 5,
        conceptual_count: int = 5,
        reasoning_count: int = 5,
        financial_count: int = 3,
        edge_count: int = 2
    ) -> List[EvaluationCase]:
        """Generate a comprehensive test suite with diverse question types."""
        
        test_suite = []
        
        # Add different types of questions
        test_suite.extend(self.generate_factual_questions(factual_count))
        test_suite.extend(self.generate_conceptual_questions(conceptual_count))
        test_suite.extend(self.generate_reasoning_questions(reasoning_count))
        test_suite.extend(self.generate_financial_questions(financial_count))
        test_suite.extend(self.generate_edge_cases(edge_count))
        
        # Shuffle to randomize order
        random.shuffle(test_suite)
        
        return test_suite
    
    def generate_stress_test_cases(self, count: int = 20) -> List[EvaluationCase]:
        """Generate a large number of test cases for stress testing."""
        return self.generate_comprehensive_test_suite(
            factual_count=count//4,
            conceptual_count=count//4,
            reasoning_count=count//4,
            financial_count=count//8,
            edge_count=count//8
        )

# Example usage
def test_synthetic_generator():
    """Test the synthetic data generator."""
    generator = SyntheticDataGenerator()
    
    # Generate different types of questions
    factual = generator.generate_factual_questions(3)
    conceptual = generator.generate_conceptual_questions(3)
    reasoning = generator.generate_reasoning_questions(3)
    financial = generator.generate_financial_questions(2)
    
    print("Generated Test Cases:")
    print("=" * 50)
    
    for category, cases in [
        ("Factual", factual),
        ("Conceptual", conceptual), 
        ("Reasoning", reasoning),
        ("Financial", financial)
    ]:
        print(f"\n{category} Questions:")
        for case in cases:
            print(f"  - {case.question}")

if __name__ == "__main__":
    test_synthetic_generator()