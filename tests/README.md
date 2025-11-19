# Tests for SQS Search Segmenter

This directory contains comprehensive tests for all important business logic in the SQS Search Segmenter application.

## Test Structure

```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Shared fixtures and test configuration
├── test_identifier.py             # Tests for ID generation
├── test_segmentation.py           # Tests for text segmentation logic
├── test_storage.py                # Tests for Firebase Storage operations
├── test_neo4j_database.py         # Tests for Neo4j database operations
├── test_milvus_database.py        # Tests for Milvus vector database operations
├── test_tasks.py                  # Tests for main task processing logic
├── test_sqs_service.py            # Tests for SQS consumer
├── test_neo4j_queries.py          # Tests for Neo4j query builders
└── test_config.py                 # Tests for configuration management
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_tasks.py
```

### Run Specific Test Class
```bash
pytest tests/test_tasks.py::TestProcessManifestationTask
```

### Run Specific Test Method
```bash
pytest tests/test_tasks.py::TestProcessManifestationTask::test_process_manifestation_task_success_new_segments
```

### Run Tests with Coverage Report
```bash
pytest --cov=app --cov-report=html
```

Then open `htmlcov/index.html` in your browser to see detailed coverage.

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests and Show Print Statements
```bash
pytest -s
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests excluding slow tests
pytest -m "not slow"
```

## Test Coverage

The test suite covers the following components:

### 1. **Identifier (test_identifier.py)**
- ID generation with various lengths
- Character validation
- Uniqueness verification

### 2. **Segmentation (test_segmentation.py)**
- Text segmentation with different languages
- Segment content extraction
- Overlapping segment handling
- Boundary condition handling

### 3. **Storage (test_storage.py)**
- Firebase initialization
- Base text retrieval from Firebase Storage
- Error handling for missing files
- Configuration validation

### 4. **Neo4j Database (test_neo4j_database.py)**
- Database initialization
- Expression ID retrieval by manifestation ID
- Search segment creation and retrieval
- Overlapping segment queries
- Error handling

### 5. **Milvus Database (test_milvus_database.py)**
- Segment embedding generation
- Vector database upload
- Batch processing
- Error handling

### 6. **Tasks (test_tasks.py)**
- Complete task processing workflow
- New segment creation flow
- Existing segment retrieval flow
- Error handling at each step
- Overlapping segment processing

### 7. **SQS Service (test_sqs_service.py)**
- Message parsing
- Task invocation
- Error handling
- Invalid message handling

### 8. **Neo4j Queries (test_neo4j_queries.py)**
- Query template generation
- Query parameter validation
- All query types coverage

### 9. **Config (test_config.py)**
- Environment-specific configuration
- Default values
- Configuration retrieval

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `mock_neo4j_driver`: Mock Neo4j driver
- `mock_firebase_storage`: Mock Firebase Storage
- `mock_milvus_client`: Mock Milvus client
- `sample_manifestation_id`: Sample test IDs
- `sample_base_text`: Sample Tibetan text
- `sample_segments`: Sample segmentation results
- `mock_env_vars`: Mock environment variables
- `mock_segment_text`: Mock segmentation function
- `mock_embed_texts_batch`: Mock embedding function

## Writing New Tests

When adding new tests:

1. **Follow the naming convention**: `test_*.py` for files, `Test*` for classes, `test_*` for methods
2. **Use descriptive test names**: Test names should clearly indicate what is being tested
3. **Use fixtures**: Leverage existing fixtures in `conftest.py` or create new ones
4. **Mock external dependencies**: Always mock database connections, API calls, and file I/O
5. **Test edge cases**: Include tests for error conditions, boundary values, and invalid inputs
6. **Add docstrings**: Include clear docstrings explaining what each test validates

### Example Test Structure

```python
class TestMyComponent:
    """Test suite for MyComponent."""
    
    def test_my_function_success(self, mock_dependency):
        """Test successful execution of my_function."""
        # Arrange
        mock_dependency.return_value = "expected_value"
        
        # Act
        result = my_function()
        
        # Assert
        assert result == "expected_value"
        mock_dependency.assert_called_once()
    
    def test_my_function_error_handling(self, mock_dependency):
        """Test error handling in my_function."""
        # Arrange
        mock_dependency.side_effect = Exception("Error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Error"):
            my_function()
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. The test suite:

- Uses mocks to avoid external dependencies
- Runs quickly (< 1 minute for full suite)
- Provides clear failure messages
- Generates coverage reports

## Troubleshooting

### Import Errors
If you encounter import errors, ensure you're running tests from the project root:
```bash
cd /path/to/sqs-search-segmenter
pytest
```

### Mock Issues
If mocks aren't working as expected:
1. Check the import path in the `@patch` decorator
2. Ensure you're patching where the object is used, not where it's defined
3. Verify mock setup is done before the code under test runs

### Coverage Issues
To see which lines aren't covered:
```bash
pytest --cov=app --cov-report=term-missing
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Clarity**: Test names and assertions should be self-documenting
3. **Speed**: Keep tests fast by mocking external dependencies
4. **Coverage**: Aim for >80% code coverage
5. **Maintenance**: Update tests when business logic changes
6. **Documentation**: Add comments for complex test scenarios

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Pytest-cov Documentation](https://pytest-cov.readthedocs.io/)

