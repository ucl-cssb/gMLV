import pytest
import numpy as np
from unittest.mock import patch
import pymc as pm
from mimic.model_infer.infer_VAR_bayes import infer_VAR


@pytest.fixture
def example_data():
    return np.random.rand(10, 3)


@pytest.fixture
def example_metabolite_data():
    return np.random.rand(10, 2)


def test_initialization(example_data):
    # Test initialization without data
    model = infer_VAR()
    assert model.data is None
    assert model.dataS is None
    assert model.coefficients is None

    # Test initialization with data
    model = infer_VAR(data=example_data)
    assert model.data is not None and model.data.shape == (10, 3)


def test_run_inference(example_data):
    # Initialize the model with data
    model = infer_VAR(data=example_data)

    # Mock pymc's sample method to avoid actual sampling
    with patch.object(pm, 'sample', return_value='mock_trace') as mock_sample:
        model.run_inference(samples=500, tune=200, cores=2)
        mock_sample.assert_called_once_with(500, tune=200, cores=2)

    # Test for error with invalid data (only 1 timepoint)
    model.data = np.random.rand(1, 3)
    with pytest.raises(ValueError):
        model.run_inference()


def test_run_inference_large(example_data):
    # Create larger dummy data
    data = np.random.rand(50, 3)

    # Initialize the model with data
    model = infer_VAR(data=data)

    # Mock pymc's sample method
    with patch.object(pm, 'sample', return_value='mock_trace') as mock_sample:
        model.run_inference_large(samples=1000, tune=500, cores=4)
        mock_sample.assert_called_once_with(1000, tune=500, cores=4)


def test_run_inference_xs(example_data, example_metabolite_data):
    # Initialize the model with data and metabolite data
    model = infer_VAR(data=example_data, dataS=example_metabolite_data)

    # Mock pymc's sample method
    with patch.object(pm, 'sample', return_value='mock_trace') as mock_sample:
        model.run_inference_xs(samples=500, tune=200, cores=2)
        mock_sample.assert_called_once_with(500, tune=200, cores=2)

    # Test for missing metabolite data
    model.dataS = None
    with pytest.raises(ValueError):
        model.run_inference_xs()


def test_posterior_analysis(mocker, example_data, example_metabolite_data):
    # Mock arviz.from_netcdf
    mocker.patch('arviz.from_netcdf', return_value='mock_inference_data')

    model = infer_VAR(data=example_data, dataS=example_metabolite_data)

    # Mock plotting and saving methods
    mock_plot_heatmap = mocker.patch.object(model, 'plot_heatmap')
    model.posterior_analysis(netcdf_filename="mock.nc")

    # Check if plot_heatmap was called
    mock_plot_heatmap.assert_called_once()
