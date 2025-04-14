import React, { useState, useEffect } from "react";
import {
  LLMProvider,
  LLMModel,
  fetchLLMProviders,
  fetchLLMModels,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
  LLMProviderCreate,
  LLMModelCreate,
} from "../../services/api";
import "./Admin.css";

const LLMModels: React.FC = () => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form states
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(
    null
  );
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [newProvider, setNewProvider] = useState<LLMProviderCreate>({
    name: "",
    description: "",
    enabled: true,
  });
  const [newModel, setNewModel] = useState<LLMModelCreate>({
    provider_id: 0,
    name: "",
    display_name: "",
    default_temperature: 0.7,
  });

  useEffect(() => {
    loadProviders();
  }, []);

  useEffect(() => {
    if (selectedProviderId) {
      loadModels(selectedProviderId);
    } else {
      loadModels();
    }
  }, [selectedProviderId]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const providersData = await fetchLLMProviders();
      setProviders(providersData);

      // Select the first provider by default if none is selected
      if (providersData.length > 0 && !selectedProviderId) {
        setSelectedProviderId(providersData[0].id);
        setNewModel((prev) => ({ ...prev, provider_id: providersData[0].id }));
      }

      setError(null);
    } catch (err: any) {
      setError(`Error loading providers: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async (providerId?: number) => {
    try {
      setLoading(true);
      const modelsData = await fetchLLMModels(providerId);
      console.log("Loaded models with provider data:", modelsData);
      setModels(modelsData);
      setError(null);
    } catch (err: any) {
      setError(`Error loading models: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setNewProvider((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleModelChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setNewModel((prev) => ({
      ...prev,
      [name]:
        name === "provider_id" || name === "default_temperature"
          ? parseFloat(value)
          : value,
    }));
  };

  const handleAddProvider = async () => {
    try {
      setLoading(true);
      const result = await createLLMProvider(newProvider);
      setSuccess(`Provider created successfully: ${result.message}`);
      setNewProvider({
        name: "",
        description: "",
        enabled: true,
      });
      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error creating provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProvider = async (
    id: number,
    provider: Partial<LLMProviderCreate>
  ) => {
    try {
      setLoading(true);
      const result = await updateLLMProvider(id, provider);
      setSuccess(`Provider updated successfully: ${result.message}`);
      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error updating provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProvider = async (id: number) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this provider? All associated models will also be deleted."
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteLLMProvider(id);
      setSuccess(`Provider deleted successfully: ${result.message}`);

      // Reset selected provider if the deleted one was selected
      if (selectedProviderId === id) {
        setSelectedProviderId(null);
      }

      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error deleting provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddModel = async () => {
    try {
      if (!newModel.provider_id) {
        setError("Please select a provider for the model");
        return;
      }

      setLoading(true);
      const result = await createLLMModel(newModel);
      setSuccess(`Model created successfully: ${result.message}`);
      setNewModel({
        provider_id: selectedProviderId || 0,
        name: "",
        display_name: "",
        default_temperature: 0.7,
      });
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error creating model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateModel = async (
    id: number,
    model: Partial<LLMModelCreate>
  ) => {
    try {
      setLoading(true);
      const result = await updateLLMModel(id, model);
      setSuccess(`Model updated successfully: ${result.message}`);
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error updating model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteModel = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this model?")) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteLLMModel(id);
      setSuccess(`Model deleted successfully: ${result.message}`);
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error deleting model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="llm-models-container">
      <h2 className="section-title">LLM Providers and Models</h2>

      {error && (
        <div className="alert alert-danger">
          {error}
          <button className="close-btn" onClick={clearMessages}>
            ×
          </button>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          {success}
          <button className="close-btn" onClick={clearMessages}>
            ×
          </button>
        </div>
      )}

      <div className="llm-sections">
        {/* Providers Section */}
        <div className="llm-providers-section">
          <h3>Providers</h3>

          <div className="provider-list">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className={`provider-item ${
                  selectedProviderId === provider.id ? "selected" : ""
                }`}
                onClick={() => setSelectedProviderId(provider.id)}
              >
                <div className="provider-name">{provider.name}</div>
                <div className="provider-actions">
                  <button
                    className="btn-danger btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteProvider(provider.id);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="add-provider-form">
            <h4>Add Provider</h4>
            <div className="form-group">
              <label>Provider Name:</label>
              <input
                type="text"
                name="name"
                value={newProvider.name}
                onChange={handleProviderChange}
                placeholder="e.g. Anthropic, OpenAI, Google"
              />
            </div>

            <div className="form-group">
              <label>Description:</label>
              <textarea
                name="description"
                value={newProvider.description}
                onChange={handleProviderChange}
                placeholder="Provider description"
              />
            </div>

            <button
              className="btn-primary"
              onClick={handleAddProvider}
              disabled={loading || !newProvider.name}
            >
              {loading ? "Adding..." : "Add Provider"}
            </button>
          </div>
        </div>

        {/* Models Section */}
        <div className="llm-models-section">
          <h3>
            Models{" "}
            {selectedProviderId &&
              `(${providers.find((p) => p.id === selectedProviderId)?.name})`}
          </h3>

          <div className="model-list">
            {models.length === 0 ? (
              <div className="no-models">No models found. Add a new model.</div>
            ) : (
              models.map((model) => (
                <div key={model.id} className="model-item">
                  <div className="model-info">
                    <div className="model-name">{model.display_name}</div>
                    <div className="model-id">ID: {model.name}</div>
                    <div className="model-temp">
                      Default Temp: {model.default_temperature}
                    </div>
                    <div className="model-provider">
                      Provider:{" "}
                      {model.provider ? model.provider.name : "Unknown"}
                    </div>
                  </div>
                  <div className="model-actions">
                    <button
                      className="btn-danger btn-sm"
                      onClick={() => handleDeleteModel(model.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="add-model-form">
            <h4>Add Model</h4>
            <div className="form-group">
              <label>Provider:</label>
              <select
                name="provider_id"
                value={newModel.provider_id || ""}
                onChange={handleModelChange}
              >
                <option value="">-- Select Provider --</option>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Model ID/Name:</label>
              <input
                type="text"
                name="name"
                value={newModel.name}
                onChange={handleModelChange}
                placeholder="e.g. claude-3-5-sonnet-20240620"
              />
            </div>

            <div className="form-group">
              <label>Display Name:</label>
              <input
                type="text"
                name="display_name"
                value={newModel.display_name}
                onChange={handleModelChange}
                placeholder="e.g. Claude 3.5 Sonnet"
              />
            </div>

            <div className="form-group">
              <label>Default Temperature:</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                name="default_temperature"
                value={newModel.default_temperature}
                onChange={handleModelChange}
              />
            </div>

            <button
              className="btn-primary"
              onClick={handleAddModel}
              disabled={
                loading ||
                !newModel.name ||
                !newModel.display_name ||
                !newModel.provider_id
              }
            >
              {loading ? "Adding..." : "Add Model"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LLMModels;
